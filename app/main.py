from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .config import ADMIN_PASSWORD, ADMIN_USER, BASE_DIR, EXPORT_DIR, FORCE_SECURE_COOKIE, SECRET_KEY
from .database import Base, engine, get_db
from .models import AuditLog, DeletionRequest, Folha, FolhaItem, Programa, Remessa, Secretaria, UnidadeGestora, User, ValidationIssue
from .security import audit, get_csrf_token, hash_password, require_login, require_role, validate_csrf, verify_password
from .display import issue_label, mask_cpf, status_label
from .catalogos import CRITERIOS_ELEGIBILIDADE, FORMAS_PAGAMENTO, POPULACOES_ATENDIDAS
from .services import (
    build_programa_criterios_json,
    exportar_folha_xlsx,
    exportar_remessa,
    gerar_modelo_csv,
    gerar_modelo_xlsx,
    gerar_modelo_programa_xlsx,
    importar_itens,
    make_item_from_form,
    validate_folha,
)

app = FastAPI(title="Hub Municipal Deliberação 361")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, https_only=FORCE_SECURE_COOKIE, same_site="lax")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.filters["mask_cpf"] = mask_cpf
templates.env.filters["status_label"] = status_label
templates.env.filters["issue_label"] = issue_label

# Perfis revisados: o antigo SECRETARIA_ENVIO foi removido.
# O gestor do benefício, dentro da Secretaria, cadastra programa, cria folha, certifica e gera o JSON.
ROLES = [
    "ADMIN",
    "SECRETARIA_OPERADOR",   # lança/importa/corrige dados da própria secretaria
    "SECRETARIA_GESTOR",     # cadastra programa, cria folha, certifica e gera JSON da própria secretaria
    "SECRETARIA_CONSULTA",   # somente leitura da própria secretaria
    "CGM_CONSULTA",          # somente acompanhamento/auditoria, sem aprovar ou validar tecnicamente
]
SECRETARIA_ROLES = {"SECRETARIA_OPERADOR", "SECRETARIA_GESTOR", "SECRETARIA_CONSULTA"}
GLOBAL_READ_ROLES = {"ADMIN", "CGM_CONSULTA"}
WRITE_ROLES = {"ADMIN", "SECRETARIA_OPERADOR", "SECRETARIA_GESTOR"}
VALIDATE_ROLES = {"ADMIN", "SECRETARIA_OPERADOR", "SECRETARIA_GESTOR"}
CERTIFY_ROLES = {"ADMIN", "SECRETARIA_GESTOR"}
EXPORT_ROLES = {"ADMIN", "SECRETARIA_GESTOR"}


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        if not db.scalar(select(User).where(User.username == ADMIN_USER)):
            db.add(User(username=ADMIN_USER, password_hash=hash_password(ADMIN_PASSWORD), role="ADMIN"))
        if db.scalar(select(func.count()).select_from(Secretaria)) == 0:
            s1 = Secretaria(nome="Secretaria Municipal de Desenvolvimento Social", sigla="SMDS")
            s2 = Secretaria(nome="Secretaria Municipal de Educação", sigla="SME")
            db.add_all([s1, s2]); db.flush()
            ug = UnidadeGestora(nome="Prefeitura Municipal", codigo_etce=1, secretaria_id=s1.id)
            db.add(ug); db.flush()
            db.add(Programa(
                nome="Programa Exemplo - Cadastro Pendente",
                codigo_etce=1,
                secretaria_id=s1.id,
                unidade_id=ug.id,
                norma_instituidora="Norma a informar",
                vigente=True,
                homologado_etce=False,
                criterios_padrao_json='[{"identificadorCriterio":1,"valorAssociado":"Critério social cadastrado","aplicavel":"S"}]',
            ))
        db.commit()
    finally:
        db.close()


@app.on_event("startup")
def startup() -> None:
    init_db()


def ctx(request: Request, db: Session, user: User | None = None, **extra):
    mask_sensitive = bool(user and user.role in {"SECRETARIA_CONSULTA", "CGM_CONSULTA"})
    data = {
        "request": request,
        "user": user,
        "csrf_token": get_csrf_token(request),
        "roles": ROLES,
        "mask_sensitive": mask_sensitive,
        "criterios_catalogo": CRITERIOS_ELEGIBILIDADE,
        "formas_pagamento": FORMAS_PAGAMENTO,
        "populacoes_atendidas": POPULACOES_ATENDIDAS,
    }
    data.update(extra)
    return data


def current_user(request: Request, db: Annotated[Session, Depends(get_db)]) -> User:
    return require_login(request, db)


def is_secretaria_user(user: User) -> bool:
    return user.role in SECRETARIA_ROLES


def assert_secretaria_bound(user: User) -> None:
    if is_secretaria_user(user) and not user.secretaria_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Usuário de Secretaria precisa estar vinculado a uma Secretaria.")


def can_access_secretaria(user: User, secretaria_id: int) -> bool:
    if user.role in GLOBAL_READ_ROLES:
        return True
    return is_secretaria_user(user) and user.secretaria_id == secretaria_id


def require_secretaria_access(user: User, secretaria_id: int) -> None:
    assert_secretaria_bound(user)
    if not can_access_secretaria(user, secretaria_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso restrito à Secretaria vinculada ao usuário.")


def require_program_access(user: User, programa: Programa) -> None:
    require_secretaria_access(user, programa.secretaria_id)


def require_folha_access(user: User, folha: Folha) -> None:
    require_program_access(user, folha.programa)


def scoped_programas_query(user: User):
    stmt = select(Programa).order_by(Programa.nome)
    if is_secretaria_user(user):
        assert_secretaria_bound(user)
        stmt = stmt.where(Programa.secretaria_id == user.secretaria_id)
    return stmt


def scoped_folhas_query(user: User):
    stmt = select(Folha).join(Programa).order_by(Folha.updated_at.desc())
    if is_secretaria_user(user):
        assert_secretaria_bound(user)
        stmt = stmt.where(Programa.secretaria_id == user.secretaria_id)
    return stmt


def scoped_secretarias_query(user: User):
    stmt = select(Secretaria).order_by(Secretaria.sigla)
    if is_secretaria_user(user):
        assert_secretaria_bound(user)
        stmt = stmt.where(Secretaria.id == user.secretaria_id)
    return stmt


def scoped_unidades_query(user: User):
    stmt = select(UnidadeGestora).order_by(UnidadeGestora.nome)
    if is_secretaria_user(user):
        assert_secretaria_bound(user)
        stmt = stmt.where(UnidadeGestora.secretaria_id == user.secretaria_id)
    return stmt


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 303 and exc.headers and "Location" in exc.headers:
        return RedirectResponse(exc.headers["Location"], status_code=303)
    return templates.TemplateResponse("error.html", {"request": request, "detail": exc.detail}, status_code=exc.status_code)


@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request, db: Annotated[Session, Depends(get_db)]):
    return templates.TemplateResponse("login.html", ctx(request, db, error=None))


@app.post("/login")
def login_post(request: Request, db: Annotated[Session, Depends(get_db)], username: str = Form(...), password: str = Form(...), csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token)
    user = db.scalar(select(User).where(User.username == username, User.is_active == True))
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", ctx(request, db, error="Usuário ou senha inválidos."), status_code=400)
    request.session["user_id"] = user.id
    audit(db, request, user, "LOGIN", "User", user.id)
    return RedirectResponse("/", status_code=303)


@app.post("/logout")
def logout(request: Request, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)], csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token)
    audit(db, request, user, "LOGOUT", "User", user.id)
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)]):
    folhas_stmt = scoped_folhas_query(user)
    folhas = db.scalars(folhas_stmt.limit(8)).all()
    folha_ids = [f.id for f in db.scalars(scoped_folhas_query(user)).all()]
    total_folhas = len(folha_ids)
    total_itens = db.scalar(select(func.count()).select_from(FolhaItem).where(FolhaItem.folha_id.in_(folha_ids))) if folha_ids else 0
    total_erros = db.scalar(select(func.count()).select_from(ValidationIssue).where(ValidationIssue.folha_id.in_(folha_ids), ValidationIssue.severity == "BLOCK")) if folha_ids else 0
    total_alertas = db.scalar(select(func.count()).select_from(ValidationIssue).where(ValidationIssue.folha_id.in_(folha_ids), ValidationIssue.severity == "ALERT")) if folha_ids else 0
    return templates.TemplateResponse("dashboard.html", ctx(request, db, user, total_folhas=total_folhas or 0, total_itens=total_itens or 0, total_erros=total_erros or 0, total_alertas=total_alertas or 0, folhas=folhas))


@app.get("/cadastros", response_class=HTMLResponse)
def cadastros(request: Request, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)]):
    secretarias = db.scalars(scoped_secretarias_query(user)).all()
    unidades = db.scalars(scoped_unidades_query(user)).all()
    programas = db.scalars(scoped_programas_query(user)).all()
    return templates.TemplateResponse("cadastros.html", ctx(request, db, user, secretarias=secretarias, unidades=unidades, programas=programas))


@app.post("/secretarias")
def criar_secretaria(request: Request, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)], nome: str = Form(...), sigla: str = Form(...), csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token); require_role(user, ["ADMIN"])
    s = Secretaria(nome=nome.strip(), sigla=sigla.strip().upper())
    db.add(s)
    try:
        db.commit(); db.refresh(s)
    except IntegrityError:
        db.rollback(); raise HTTPException(400, "Sigla já cadastrada.")
    audit(db, request, user, "CRIAR", "Secretaria", s.id, s.sigla)
    return RedirectResponse("/cadastros", status_code=303)


@app.post("/unidades")
def criar_unidade(request: Request, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)], nome: str = Form(...), codigo_etce: int = Form(...), secretaria_id: int = Form(...), csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token); require_role(user, ["ADMIN"])
    ug = UnidadeGestora(nome=nome.strip(), codigo_etce=codigo_etce, secretaria_id=secretaria_id)
    db.add(ug)
    try:
        db.commit(); db.refresh(ug)
    except IntegrityError:
        db.rollback(); raise HTTPException(400, "Código e-TCERJ da unidade já cadastrado.")
    audit(db, request, user, "CRIAR", "UnidadeGestora", ug.id, str(codigo_etce))
    return RedirectResponse("/cadastros", status_code=303)


@app.post("/programas")
def criar_programa(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
    nome: str = Form(...),
    unidade_id: int = Form(...),
    codigo_etce: str = Form(""),
    norma_instituidora: str = Form(""),
    valor_individual: str = Form(""),
    forma_pagamento: str = Form(""),
    unidade_orcamentaria: str = Form(""),
    populacoes: list[str] = Form(default=[]),
    criterio_ids: list[str] = Form(default=[]),
    limite_inferior: str = Form(""),
    limite_superior: str = Form(""),
    criterio_vigencia_inicio: str = Form(""),
    criterio_vigencia_fim: str = Form(""),
    prazo_indeterminado: str = Form("off"),
    vigente: str = Form("off"),
    homologado_etce: str = Form("off"),
    csrf_token: str = Form(...),
):
    validate_csrf(request, csrf_token)
    # Conforme a regra definida para o Município, somente o gestor da Secretaria cria programas.
    require_role(user, ["SECRETARIA_GESTOR"])
    assert_secretaria_bound(user)
    secretaria_id = int(user.secretaria_id)
    unidade = db.get(UnidadeGestora, unidade_id)
    if not unidade:
        raise HTTPException(404, "Unidade Gestora não localizada.")
    if unidade.secretaria_id != secretaria_id:
        raise HTTPException(400, "A Unidade Gestora deve pertencer à Secretaria do programa.")
    criterios_json = build_programa_criterios_json(
        criterio_ids,
        limite_inferior=limite_inferior,
        limite_superior=limite_superior,
        vigencia_inicio=criterio_vigencia_inicio,
        vigencia_fim=criterio_vigencia_fim,
        prazo_indeterminado=(prazo_indeterminado == "on"),
    )
    meta = {
        "valorIndividual": valor_individual.strip(),
        "formaPagamento": forma_pagamento.strip(),
        "unidadeOrcamentaria": unidade_orcamentaria.strip(),
        "populacoesAtendidas": populacoes,
    }
    norma = (norma_instituidora.strip() or "") + "\n\n[META_PROGRAMA] " + __import__("json").dumps(meta, ensure_ascii=False)
    p = Programa(
        nome=nome.strip(),
        secretaria_id=secretaria_id,
        unidade_id=unidade_id,
        codigo_etce=int(codigo_etce) if str(codigo_etce).strip() else None,
        norma_instituidora=norma.strip() or None,
        vigente=vigente == "on",
        homologado_etce=homologado_etce == "on",
        criterios_padrao_json=criterios_json,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    audit(db, request, user, "CRIAR", "Programa", p.id, p.nome)
    return RedirectResponse("/cadastros", status_code=303)


@app.get("/folhas", response_class=HTMLResponse)
def folhas(request: Request, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)]):
    folhas = db.scalars(scoped_folhas_query(user)).all()
    programas = db.scalars(scoped_programas_query(user)).all()
    return templates.TemplateResponse("folhas.html", ctx(request, db, user, folhas=folhas, programas=programas))


@app.post("/folhas")
def criar_folha(request: Request, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)], programa_id: int = Form(...), ano: str = Form(...), mes: int = Form(...), tipo_folha: int = Form(...), sequencial: int = Form(...), csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token); require_role(user, ["ADMIN", "SECRETARIA_OPERADOR", "SECRETARIA_GESTOR"])
    programa = db.get(Programa, programa_id)
    if not programa:
        raise HTTPException(404, "Programa não localizado.")
    require_program_access(user, programa)
    folha = Folha(programa_id=programa.id, unidade_id=programa.unidade_id, ano=ano, mes=mes, tipo_folha=tipo_folha, sequencial=sequencial, created_by=user.id)
    db.add(folha)
    try:
        db.commit(); db.refresh(folha)
    except IntegrityError:
        db.rollback(); raise HTTPException(400, "Já existe folha para este programa, competência, tipo e sequencial.")
    audit(db, request, user, "CRIAR", "Folha", folha.id, f"{ano}-{mes:02d}")
    return RedirectResponse(f"/folhas/{folha.id}", status_code=303)


@app.get("/folhas/{folha_id}", response_class=HTMLResponse)
def detalhe_folha(request: Request, folha_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)]):
    folha = db.get(Folha, folha_id)
    if not folha: raise HTTPException(404, "Folha não localizada.")
    require_folha_access(user, folha)
    issues = db.scalars(select(ValidationIssue).where(ValidationIssue.folha_id == folha.id).order_by(ValidationIssue.severity, ValidationIssue.id)).all()
    remessas = db.scalars(select(Remessa).where(Remessa.folha_id == folha.id).order_by(Remessa.created_at.desc())).all()
    return templates.TemplateResponse("folha_detail.html", ctx(request, db, user, folha=folha, issues=issues, remessas=remessas))


@app.post("/folhas/{folha_id}/itens")
async def adicionar_item(request: Request, folha_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)]):
    form = await request.form()
    validate_csrf(request, str(form.get("csrf_token"))); require_role(user, WRITE_ROLES)
    folha = db.get(Folha, folha_id)
    if not folha: raise HTTPException(404, "Folha não localizada.")
    require_folha_access(user, folha)
    try:
        item = make_item_from_form(db, folha, dict(form))
        folha.secretaria_certified_by = None
        folha.status = "RASCUNHO"
        db.commit(); db.refresh(item)
        audit(db, request, user, "ADICIONAR_ITEM", "FolhaItem", item.id, f"folha={folha.id}")
    except Exception as exc:
        db.rollback(); raise HTTPException(400, str(exc))
    return RedirectResponse(f"/folhas/{folha.id}", status_code=303)


@app.post("/folhas/{folha_id}/itens/{item_id}/delete")
def deletar_item(request: Request, folha_id: int, item_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)], csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token); require_role(user, ["ADMIN", "SECRETARIA_GESTOR"])
    folha = db.get(Folha, folha_id)
    if not folha: raise HTTPException(404, "Folha não localizada.")
    require_folha_access(user, folha)
    item = db.get(FolhaItem, item_id)
    if item and item.folha_id == folha_id:
        db.delete(item)
        folha.secretaria_certified_by = None
        folha.status = "RASCUNHO"
        db.commit(); audit(db, request, user, "EXCLUIR", "FolhaItem", item_id)
    return RedirectResponse(f"/folhas/{folha_id}", status_code=303)


@app.post("/folhas/{folha_id}/importar")
async def importar(request: Request, folha_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)], arquivo: UploadFile = File(...), csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token); require_role(user, WRITE_ROLES)
    folha = db.get(Folha, folha_id)
    if not folha: raise HTTPException(404, "Folha não localizada.")
    require_folha_access(user, folha)
    data = await arquivo.read()
    fname = (arquivo.filename or "").lower()
    if not fname.endswith((".csv", ".xlsx")):
        raise HTTPException(400, "Envie apenas arquivo .csv ou .xlsx.")
    try:
        imported, updated, errors = importar_itens(db, folha, arquivo.filename or "arquivo", data)
        folha.secretaria_certified_by = None
        folha.status = "RASCUNHO"
        db.commit()
        audit(db, request, user, "IMPORTAR", "Folha", folha.id, f"novos={imported}; atualizados={updated}; erros={len(errors)}")
        parts = [f"Novos registros: {imported}.", f"Atualizados: {updated}."]
        if errors:
            parts.append(f"Erros em {len(errors)} linha(s): " + " | ".join(errors[:8]))
            if len(errors) > 8:
                parts.append(f"... e mais {len(errors) - 8} erro(s).")
        request.session["flash"] = " ".join(parts)
    except Exception as exc:
        db.rollback(); raise HTTPException(400, str(exc))
    return RedirectResponse(f"/folhas/{folha.id}", status_code=303)


@app.post("/folhas/{folha_id}/validar")
def validar(request: Request, folha_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)], csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token); require_role(user, VALIDATE_ROLES)
    folha = db.get(Folha, folha_id)
    if not folha: raise HTTPException(404, "Folha não localizada.")
    require_folha_access(user, folha)
    blocks, alerts = validate_folha(db, folha)
    audit(db, request, user, "VALIDAR", "Folha", folha.id, f"blocks={blocks}; alerts={alerts}")
    return RedirectResponse(f"/folhas/{folha.id}", status_code=303)


@app.post("/folhas/{folha_id}/certificar-gestor")
def certificar_gestor(request: Request, folha_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)], csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token); require_role(user, CERTIFY_ROLES)
    folha = db.get(Folha, folha_id)
    if not folha: raise HTTPException(404, "Folha não localizada.")
    require_folha_access(user, folha)
    blocks, alerts = validate_folha(db, folha)
    if blocks:
        raise HTTPException(400, "Não é possível certificar: a folha possui erros bloqueantes.")
    folha.secretaria_certified_by = user.id
    folha.status = "CERTIFICADA_GESTOR"
    db.commit()
    audit(db, request, user, "CERTIFICAR_GESTOR", "Folha", folha.id, f"alerts={alerts}")
    return RedirectResponse(f"/folhas/{folha.id}", status_code=303)


@app.post("/folhas/{folha_id}/exportar")
def exportar(request: Request, folha_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)], csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token); require_role(user, EXPORT_ROLES)
    folha = db.get(Folha, folha_id)
    if not folha: raise HTTPException(404, "Folha não localizada.")
    require_folha_access(user, folha)
    if not folha.secretaria_certified_by:
        raise HTTPException(400, "A folha precisa ser certificada pelo gestor do benefício antes da geração do JSON.")
    try:
        remessa = exportar_remessa(db, folha, user)
        audit(db, request, user, "EXPORTAR_JSON", "Remessa", remessa.id, remessa.sha256)
    except Exception as exc:
        raise HTTPException(400, str(exc))
    return RedirectResponse(f"/folhas/{folha.id}", status_code=303)


@app.get("/remessas/{remessa_id}/download")
def download_remessa(remessa_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)]):
    remessa = db.get(Remessa, remessa_id)
    if not remessa: raise HTTPException(404, "Remessa não localizada.")
    require_folha_access(user, remessa.folha)
    path = EXPORT_DIR / remessa.filename
    if not path.exists(): raise HTTPException(404, "Arquivo não encontrado no servidor.")
    return FileResponse(path, media_type="application/json", filename=remessa.filename)


@app.get("/modelo-importacao")
def modelo_importacao(user: Annotated[User, Depends(current_user)]):
    return Response(content=gerar_modelo_csv(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=modelo_importacao_delib361.csv"})


@app.get("/modelo-importacao.xlsx")
def modelo_importacao_xlsx(user: Annotated[User, Depends(current_user)]):
    return Response(
        content=gerar_modelo_xlsx(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=modelo_importacao_delib361.xlsx"},
    )


@app.get("/folhas/{folha_id}/exportar-planilha")
def exportar_planilha_folha(folha_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)]):
    folha = db.get(Folha, folha_id)
    if not folha:
        raise HTTPException(404, "Folha não localizada.")
    require_folha_access(user, folha)
    content = exportar_folha_xlsx(folha)
    filename = f"folha_{folha.id}_{folha.ano}_{folha.mes:02d}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )



@app.get("/programas/{programa_id}/modelo-beneficiarios.xlsx")
def modelo_programa_xlsx(programa_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)]):
    programa = db.get(Programa, programa_id)
    if not programa:
        raise HTTPException(404, "Programa não localizado.")
    require_program_access(user, programa)
    content = gerar_modelo_programa_xlsx(programa)
    filename = f"modelo_beneficiarios_programa_{programa.id}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.post("/folhas/{folha_id}/solicitar-exclusao")
def solicitar_exclusao_folha(request: Request, folha_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)], reason: str = Form(""), csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token); require_role(user, ["SECRETARIA_GESTOR"])
    folha = db.get(Folha, folha_id)
    if not folha: raise HTTPException(404, "Folha não localizada.")
    require_folha_access(user, folha)
    req = DeletionRequest(target_type="FOLHA", target_id=folha.id, folha_id=folha.id, secretaria_id=folha.programa.secretaria_id, requested_by=user.id, status="PENDENTE_ADMIN", reason=reason.strip() or "Solicitação de exclusão da folha pelo gestor.")
    db.add(req); db.commit(); db.refresh(req)
    audit(db, request, user, "SOLICITAR_EXCLUSAO", "Folha", folha.id, req.reason)
    request.session["flash"] = "Solicitação de exclusão enviada ao ADM."
    return RedirectResponse(f"/folhas/{folha.id}", status_code=303)


@app.post("/folhas/{folha_id}/itens/{item_id}/solicitar-exclusao")
def solicitar_exclusao_item(request: Request, folha_id: int, item_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)], reason: str = Form(""), csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token); require_role(user, ["SECRETARIA_OPERADOR"])
    folha = db.get(Folha, folha_id)
    if not folha: raise HTTPException(404, "Folha não localizada.")
    require_folha_access(user, folha)
    item = db.get(FolhaItem, item_id)
    if not item or item.folha_id != folha.id: raise HTTPException(404, "Beneficiário não localizado na folha.")
    req = DeletionRequest(target_type="FOLHA_ITEM", target_id=item.id, folha_id=folha.id, secretaria_id=folha.programa.secretaria_id, requested_by=user.id, status="PENDENTE_GESTOR", reason=reason.strip() or "Solicitação de exclusão de beneficiário pelo operador.")
    db.add(req); db.commit(); db.refresh(req)
    audit(db, request, user, "SOLICITAR_EXCLUSAO", "FolhaItem", item.id, req.reason)
    request.session["flash"] = "Solicitação de exclusão enviada ao gestor da Secretaria."
    return RedirectResponse(f"/folhas/{folha.id}", status_code=303)


@app.get("/solicitacoes-exclusao", response_class=HTMLResponse)
def solicitacoes_exclusao(request: Request, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)]):
    require_role(user, ["ADMIN", "SECRETARIA_GESTOR"])
    stmt = select(DeletionRequest).order_by(DeletionRequest.created_at.desc())
    if user.role == "SECRETARIA_GESTOR":
        assert_secretaria_bound(user)
        stmt = stmt.where(DeletionRequest.secretaria_id == user.secretaria_id)
    solicitacoes = db.scalars(stmt).all()
    return templates.TemplateResponse("solicitacoes.html", ctx(request, db, user, solicitacoes=solicitacoes))


def _delete_target(db: Session, req: DeletionRequest) -> str:
    if req.target_type == "FOLHA_ITEM":
        item = db.get(FolhaItem, req.target_id)
        if not item:
            return "Beneficiário já não existia."
        folha = item.folha
        db.delete(item)
        folha.secretaria_certified_by = None
        folha.status = "RASCUNHO"
        return f"Beneficiário da folha {folha.id} excluído."
    if req.target_type == "FOLHA":
        folha = db.get(Folha, req.target_id)
        if not folha:
            return "Folha já não existia."
        db.query(ValidationIssue).filter(ValidationIssue.folha_id == folha.id).delete(synchronize_session=False)
        db.query(Remessa).filter(Remessa.folha_id == folha.id).delete(synchronize_session=False)
        db.delete(folha)
        return f"Folha {req.target_id} excluída."
    if req.target_type == "PROGRAMA":
        programa = db.get(Programa, req.target_id)
        if not programa:
            return "Programa já não existia."
        folhas = db.scalars(select(Folha).where(Folha.programa_id == programa.id)).all()
        if folhas:
            raise HTTPException(400, "Não é possível excluir programa com folhas vinculadas. Exclua as folhas antes.")
        db.delete(programa)
        return f"Programa {req.target_id} excluído."
    raise HTTPException(400, "Tipo de solicitação não suportado.")


@app.post("/solicitacoes-exclusao/{request_id}/aprovar")
def aprovar_solicitacao(request: Request, request_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)], decision_note: str = Form(""), csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token)
    req = db.get(DeletionRequest, request_id)
    if not req: raise HTTPException(404, "Solicitação não localizada.")
    if req.status == "PENDENTE_GESTOR":
        require_role(user, ["SECRETARIA_GESTOR", "ADMIN"])
        if user.role == "SECRETARIA_GESTOR":
            require_secretaria_access(user, req.secretaria_id or 0)
    else:
        require_role(user, ["ADMIN"])
    msg = _delete_target(db, req)
    req.status = "APROVADA"
    req.decided_by = user.id
    req.decision_note = decision_note.strip() or msg
    from datetime import datetime
    req.decided_at = datetime.utcnow()
    db.commit()
    audit(db, request, user, "APROVAR_EXCLUSAO", req.target_type, req.target_id, msg)
    request.session["flash"] = msg
    return RedirectResponse("/solicitacoes-exclusao", status_code=303)


@app.post("/solicitacoes-exclusao/{request_id}/recusar")
def recusar_solicitacao(request: Request, request_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)], decision_note: str = Form(""), csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token)
    req = db.get(DeletionRequest, request_id)
    if not req: raise HTTPException(404, "Solicitação não localizada.")
    if req.status == "PENDENTE_GESTOR":
        require_role(user, ["SECRETARIA_GESTOR", "ADMIN"])
        if user.role == "SECRETARIA_GESTOR":
            require_secretaria_access(user, req.secretaria_id or 0)
    else:
        require_role(user, ["ADMIN"])
    req.status = "RECUSADA"
    req.decided_by = user.id
    req.decision_note = decision_note.strip() or "Solicitação recusada."
    from datetime import datetime
    req.decided_at = datetime.utcnow()
    db.commit()
    audit(db, request, user, "RECUSAR_EXCLUSAO", req.target_type, req.target_id, req.decision_note)
    return RedirectResponse("/solicitacoes-exclusao", status_code=303)


@app.post("/admin/folhas/{folha_id}/delete")
def admin_delete_folha(request: Request, folha_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)], csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token); require_role(user, ["ADMIN"])
    folha = db.get(Folha, folha_id)
    if not folha: raise HTTPException(404, "Folha não localizada.")
    req = DeletionRequest(target_type="FOLHA", target_id=folha.id, folha_id=folha.id, secretaria_id=folha.programa.secretaria_id, requested_by=user.id, status="PENDENTE_ADMIN", reason="Exclusão direta pelo ADM")
    db.add(req); db.flush()
    msg = _delete_target(db, req)
    req.status = "APROVADA"; req.decided_by = user.id; req.decision_note = msg
    from datetime import datetime
    req.decided_at = datetime.utcnow()
    db.commit(); audit(db, request, user, "EXCLUIR_DIRETO", "Folha", folha_id, msg)
    request.session["flash"] = msg
    return RedirectResponse("/folhas", status_code=303)


@app.post("/admin/usuarios/{usuario_id}/delete")
def admin_delete_usuario(request: Request, usuario_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)], csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token); require_role(user, ["ADMIN"])
    target = db.get(User, usuario_id)
    if not target: raise HTTPException(404, "Usuário não localizado.")
    if target.id == user.id: raise HTTPException(400, "O ADM logado não pode desativar a si próprio.")
    target.is_active = False
    db.commit(); audit(db, request, user, "DESATIVAR", "User", target.id, target.username)
    return RedirectResponse("/usuarios", status_code=303)


@app.post("/admin/secretarias/{secretaria_id}/delete")
def admin_delete_secretaria(request: Request, secretaria_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)], csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token); require_role(user, ["ADMIN"])
    sec = db.get(Secretaria, secretaria_id)
    if not sec: raise HTTPException(404, "Secretaria não localizada.")
    has_programa = db.scalar(select(Programa.id).where(Programa.secretaria_id == sec.id))
    has_ug = db.scalar(select(UnidadeGestora.id).where(UnidadeGestora.secretaria_id == sec.id))
    if has_programa or has_ug:
        sec.ativa = False
        db.commit(); audit(db, request, user, "DESATIVAR", "Secretaria", sec.id, sec.sigla)
        request.session["flash"] = "Secretaria possui vínculos e foi desativada, preservando histórico."
    else:
        db.delete(sec); db.commit(); audit(db, request, user, "EXCLUIR", "Secretaria", secretaria_id)
    return RedirectResponse("/cadastros", status_code=303)


@app.post("/admin/unidades/{unidade_id}/delete")
def admin_delete_unidade(request: Request, unidade_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)], csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token); require_role(user, ["ADMIN"])
    ug = db.get(UnidadeGestora, unidade_id)
    if not ug: raise HTTPException(404, "UG não localizada.")
    has_programa = db.scalar(select(Programa.id).where(Programa.unidade_id == ug.id))
    if has_programa:
        raise HTTPException(400, "Não é possível excluir UG com programas vinculados. Exclua/migre os programas antes.")
    db.delete(ug); db.commit(); audit(db, request, user, "EXCLUIR", "UnidadeGestora", unidade_id)
    return RedirectResponse("/cadastros", status_code=303)


@app.get("/usuarios", response_class=HTMLResponse)
def usuarios(request: Request, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)]):
    require_role(user, ["ADMIN"])
    users = db.scalars(select(User).order_by(User.username)).all()
    secretarias = db.scalars(select(Secretaria).order_by(Secretaria.sigla)).all()
    return templates.TemplateResponse("usuarios.html", ctx(request, db, user, users=users, secretarias=secretarias))


@app.post("/usuarios")
def criar_usuario(request: Request, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)], username: str = Form(...), password: str = Form(...), role: str = Form(...), secretaria_id: str = Form(""), csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token); require_role(user, ["ADMIN"])
    if role not in ROLES: raise HTTPException(400, "Perfil inválido.")
    if role in SECRETARIA_ROLES and not secretaria_id:
        raise HTTPException(400, "Perfis de Secretaria precisam estar vinculados a uma Secretaria.")
    new = User(username=username.strip(), password_hash=hash_password(password), role=role, secretaria_id=int(secretaria_id) if secretaria_id else None)
    db.add(new)
    try:
        db.commit(); db.refresh(new)
    except IntegrityError:
        db.rollback(); raise HTTPException(400, "Usuário já cadastrado.")
    audit(db, request, user, "CRIAR", "User", new.id, new.username)
    return RedirectResponse("/usuarios", status_code=303)


@app.get("/logs", response_class=HTMLResponse)
def logs(request: Request, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)]):
    require_role(user, ["ADMIN", "CGM_CONSULTA"])
    logs = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200)).all()
    return templates.TemplateResponse("logs.html", ctx(request, db, user, logs=logs))
