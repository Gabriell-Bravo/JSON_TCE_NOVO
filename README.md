# Hub Municipal de Benefícios Socioassistenciais — Deliberação TCE-RJ nº 361/2025

Sistema MVP em **Python/FastAPI**, **SQLite**, **SQLAlchemy**, **Jinja2** e **openpyxl** para que Secretarias gestoras cadastrem/importem beneficiários, validem dados, certifiquem a folha e gerem o arquivo JSON **AUDFOBEN** para o e-TCERJ.

## Fluxo operacional

1. **Operador** da Secretaria lança ou importa beneficiários.
2. O sistema executa **validações** (erros bloqueantes e alertas).
3. O operador corrige pendências.
4. O **gestor do benefício** certifica a folha.
5. O perfil de **envio** gera e baixa o JSON AUDFOBEN.
6. A **CGM** (quando cadastrada) consulta dados e auditoria, sem certificar ou validar tecnicamente.

Não há etapa de Finanças nem validação técnica obrigatória da CGM.

## Perfis de usuário

| Perfil | Função |
|--------|--------|
| `ADMIN` | Administração geral do sistema |
| `SECRETARIA_OPERADOR` | Cadastra, importa e corrige dados da própria Secretaria |
| `SECRETARIA_GESTOR` | Valida e **certifica** a folha |
| `SECRETARIA_ENVIO` | **Gera e baixa** o JSON após certificação |
| `SECRETARIA_CONSULTA` | Somente leitura (CPF parcialmente mascarado) |
| `CGM_CONSULTA` | Consulta geral e logs de auditoria |

Usuários de Secretaria devem estar vinculados a uma Secretaria. O acesso a folhas e programas é filtrado por essa vinculação.

## Instalação no Windows (VS Code)

```powershell
cd delib361_hub
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Acesse: **http://127.0.0.1:8000**

Usuário inicial: `admin` / `Admin@12345`

Variáveis de ambiente úteis:

```powershell
set APP_ADMIN_PASSWORD=uma-senha-forte
set APP_SECRET_KEY=chave-aleatoria-longa
set APP_FORCE_SECURE_COOKIE=true
set APP_DATABASE_URL=sqlite:///caminho/custom.db
```

## Estrutura de pastas

```
delib361_hub/
  app/
    main.py           # rotas FastAPI
    models.py         # modelos SQLAlchemy
    services.py       # importação, validação, JSON
    validators.py     # regras de negócio
    security.py       # autenticação, CSRF, auditoria
    schema/audfoben.json   # schema oficial AUDFOBEN
    templates/        # telas HTML
    static/           # CSS
    data/             # banco SQLite e JSONs exportados
  tests/              # testes automatizados
  run.py              # entrada do servidor
  requirements.txt
```

## Importação e exportação de planilhas

**Modelos:** menu lateral → Modelo CSV ou Modelo Excel.

**Colunas aceitas:**

`item_id`, `cpf`, `numeroNIS`, `nome`, `sexo`, `dataNascimento`, `nacionalidade`, `nomeMae`, `enderecoCEP`, `logradouro`, `bairro`, `numero`, `complemento`, `codigoIBGEMunicipio`, `valorTotalTransferido`, `totalPessoasBeneficio`, `totalDependentesBeneficio`, `criterio_id`, `criterio_valor`, `criterio_aplicavel`, `dependentes_json`, `evidencia`

**Reimportação sem duplicar:**
- Informe `item_id` (exportado na planilha da folha) para atualizar o registro.
- Sem `item_id`, o sistema atualiza pelo **CPF** se já existir na folha.

**Exportar planilha atual:** na tela da folha → *Exportar planilha atual (.xlsx)*.

## Validações

- Erros **bloqueantes** impedem certificação e geração do JSON.
- **Alertas** permitem continuar, mas ficam registrados para conferência.

Regras principais: CPF válido, duplicidade na folha, NIS com 11 dígitos, sexo M/F, IBGE 7 dígitos, critérios obrigatórios, coerência de dependentes, programa homologado/vigente, folha suplementar exige ordinária na competência, validação final contra schema AUDFOBEN.

## Alterar validações

Edite `app/validators.py` (regras de campo) e `app/services.py` (validação da folha e montagem do JSON).

## Alterar schema AUDFOBEN

Substitua `app/schema/audfoben.json` pelo arquivo oficial do TCE-RJ. O sistema carrega automaticamente na inicialização.

## Testes

```powershell
venv\Scripts\activate
pytest tests/ -v
```

Cobertura: CPF, perfis (certificação/envio), importação com `item_id`, geração JSON, bloqueio de exportação com pendências.

## Produção

1. Migrar para **PostgreSQL** (`APP_DATABASE_URL`).
2. HTTPS + `APP_FORCE_SECURE_COOKIE=true`.
3. `APP_SECRET_KEY` forte e única.
4. Backup diário de `app/data/` e logs.
5. Restringir acesso por rede interna/VPN.
6. Integrar SSO municipal quando disponível.

## Observação

O schema em `app/schema/audfoben.json` segue a Deliberação 361/2025. Atualize-o sempre que o TCE-RJ publicar nova versão.
