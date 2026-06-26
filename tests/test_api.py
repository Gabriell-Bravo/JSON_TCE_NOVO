import csv
import io

from sqlalchemy import select

from app.models import Folha, FolhaItem, Remessa, Secretaria
from app.services import build_folha_json, gerar_modelo_xlsx, importar_itens, validate_folha
from tests.conftest import create_user, csrf_from, login_user


def _criar_folha(db, programa, ug, user_id):
    used_meses = set(
        db.scalars(
            select(Folha.mes).where(Folha.programa_id == programa.id, Folha.ano == "2026", Folha.tipo_folha == 1)
        ).all()
    )
    mes = next((m for m in range(1, 13) if m not in used_meses), 1)
    folha = Folha(
        programa_id=programa.id,
        unidade_id=ug.id,
        ano="2026",
        mes=mes,
        tipo_folha=1,
        sequencial=1,
        created_by=user_id,
    )
    db.add(folha)
    db.commit()
    db.refresh(folha)
    return folha


def _item_form():
    return {
        "cpf": "52998224725",
        "nome": "Maria da Silva",
        "sexo": "F",
        "dataNascimento": "1990-01-01",
        "nacionalidade": "Brasil",
        "logradouro": "Rua A",
        "bairro": "Centro",
        "codigoIBGEMunicipio": "3305505",
        "valorTotalTransferido": "300.00",
        "totalPessoasBeneficio": "1",
        "totalDependentesBeneficio": "0",
        "criterio_id": "11",
        "criterio_valor": "SIM",
        "criterio_aplicavel": "S",
        "dependentes_json": "[]",
        "evidencia": "Proc 1/2026",
    }


def _csv_bytes(row: dict) -> bytes:
    cols = [
        "item_id", "cpf", "numeroNIS", "nome", "sexo", "dataNascimento", "nacionalidade",
        "nomeMae", "enderecoCEP", "logradouro", "bairro", "numero", "complemento",
        "codigoIBGEMunicipio", "valorTotalTransferido", "totalPessoasBeneficio",
        "totalDependentesBeneficio", "criterio_id", "criterio_valor", "criterio_aplicavel",
        "dependentes_json", "evidencia",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    full = {"item_id": row.get("item_id", ""), **row}
    writer.writerow(full)
    return buf.getvalue().encode("utf-8-sig")


def test_gestor_pode_certificar_operador_nao(client, db, secretaria_setup):
    secretaria, ug, programa = secretaria_setup
    gestor = create_user(db, "gestor1", "SECRETARIA_GESTOR", secretaria.id)
    create_user(db, "oper1", "SECRETARIA_OPERADOR", secretaria.id)
    folha = _criar_folha(db, programa, ug, gestor.id)
    importar_itens(db, folha, "t.csv", _csv_bytes(_item_form()))
    validate_folha(db, folha)

    login_user(client, "oper1")
    token = csrf_from(client, f"/folhas/{folha.id}")
    r = client.post(f"/folhas/{folha.id}/certificar-gestor", data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code == 403

    login_user(client, "gestor1")
    token = csrf_from(client, f"/folhas/{folha.id}")
    r = client.post(f"/folhas/{folha.id}/certificar-gestor", data={"csrf_token": token}, follow_redirects=True)
    assert r.status_code == 200
    db.refresh(folha)
    assert folha.secretaria_certified_by == gestor.id


def test_gestor_gera_json_sem_perfil_envio(client, db, secretaria_setup):
    secretaria, ug, programa = secretaria_setup
    gestor = create_user(db, "gestor2", "SECRETARIA_GESTOR", secretaria.id)
    create_user(db, "consulta1", "SECRETARIA_CONSULTA", secretaria.id)
    folha = _criar_folha(db, programa, ug, gestor.id)
    importar_itens(db, folha, "t.csv", _csv_bytes(_item_form()))
    validate_folha(db, folha)
    folha.secretaria_certified_by = gestor.id
    folha.status = "CERTIFICADA_GESTOR"
    db.commit()

    login_user(client, "consulta1")
    token = csrf_from(client, f"/folhas/{folha.id}")
    r = client.post(f"/folhas/{folha.id}/exportar", data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code == 403

    login_user(client, "gestor2")
    token = csrf_from(client, f"/folhas/{folha.id}")
    r = client.post(f"/folhas/{folha.id}/exportar", data={"csrf_token": token}, follow_redirects=True)
    assert r.status_code == 200
    remessa = db.scalar(select(Remessa).where(Remessa.folha_id == folha.id))
    assert remessa is not None
    assert remessa.sha256


def test_bloqueio_exportacao_com_erro(client, db, secretaria_setup):
    secretaria, ug, programa = secretaria_setup
    gestor = create_user(db, "gestor_export_erro", "SECRETARIA_GESTOR", secretaria.id)
    folha = _criar_folha(db, programa, ug, gestor.id)
    folha.secretaria_certified_by = gestor.id
    db.commit()
    db.refresh(folha)
    assert len(folha.itens) == 0

    login_user(client, "gestor_export_erro")
    token = csrf_from(client, f"/folhas/{folha.id}")
    r = client.post(f"/folhas/{folha.id}/exportar", data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code == 400


def test_importacao_atualiza_por_item_id(db, secretaria_setup):
    _, ug, programa = secretaria_setup
    folha = _criar_folha(db, programa, ug, None)
    imported, updated, errors = importar_itens(db, folha, "t.csv", _csv_bytes(_item_form()))
    assert imported == 1 and updated == 0 and not errors
    item = db.scalar(select(FolhaItem).where(FolhaItem.folha_id == folha.id))
    row = _item_form()
    row["item_id"] = str(item.id)
    row["valorTotalTransferido"] = "450.00"
    imported2, updated2, errors2 = importar_itens(db, folha, "t.csv", _csv_bytes(row))
    assert imported2 == 0 and updated2 == 1 and not errors2
    db.refresh(item)
    assert float(item.valor_total_transferido) == 450.0


def test_json_audfoben_estrutura(db, secretaria_setup):
    _, ug, programa = secretaria_setup
    folha = _criar_folha(db, programa, ug, None)
    importar_itens(db, folha, "t.csv", _csv_bytes(_item_form()))
    validate_folha(db, folha)
    payload = build_folha_json(folha)
    assert payload["anoReferencia"] == "2026"
    assert payload["beneficios"][0]["cpf"] == "52998224725"
    assert "criterios" in payload["beneficios"][0]


def test_modelo_xlsx_gera_bytes():
    data = gerar_modelo_xlsx()
    assert data[:2] == b"PK"


def test_acesso_entre_secretarias(client, db, secretaria_setup):
    s2 = db.scalar(select(Secretaria).where(Secretaria.sigla == "SME"))
    create_user(db, "opsme", "SECRETARIA_OPERADOR", s2.id)
    folha_s1 = _criar_folha(db, secretaria_setup[2], secretaria_setup[1], None)
    login_user(client, "opsme")
    r = client.get(f"/folhas/{folha_s1.id}", follow_redirects=False)
    assert r.status_code == 403


def test_folha_bloqueada_apos_remessa_enviada(client, db, secretaria_setup):
    from app.models import Remessa
    from app.services import folha_edicao_bloqueada
    _, ug, programa = secretaria_setup
    gestor = create_user(db, "gestor_bloq", "SECRETARIA_GESTOR", secretaria_setup[0].id)
    folha = _criar_folha(db, programa, ug, gestor.id)
    importar_itens(db, folha, "t.csv", _csv_bytes(_item_form()))
    db.add(Remessa(folha_id=folha.id, filename="t.json", sha256="a" * 64, size_bytes=10, status="ENVIADA", created_by=gestor.id))
    db.commit()
    assert folha_edicao_bloqueada(db, folha) is not None
    login_user(client, "gestor_bloq")
    token = csrf_from(client, f"/folhas/{folha.id}")
    r = client.post(f"/folhas/{folha.id}/importar", data={"csrf_token": token}, files={"arquivo": ("t.csv", _csv_bytes(_item_form()), "text/csv")}, follow_redirects=False)
    assert r.status_code == 400
