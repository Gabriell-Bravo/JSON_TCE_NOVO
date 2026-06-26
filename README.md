# Hub Municipal de Benefícios Socioassistenciais — Deliberação TCE-RJ nº 361/2025

Sistema MVP funcional em **FastAPI + SQLite + Jinja2 + HTML/CSS + openpyxl + jsonschema** para apoiar Secretarias gestoras no cadastro/importação de beneficiários, validação de dados, certificação da folha e geração do JSON AUDFOBEN.

## Fluxo funcional desta versão

1. A Secretaria gestora cadastra o programa do benefício.
2. O sistema vincula ao programa seus critérios de elegibilidade previamente escolhidos no catálogo interno inspirado no e-TCERJ.
3. O gestor baixa a planilha Excel específica daquele programa.
4. O operador ou gestor importa/cadastra beneficiários.
5. O sistema valida campos obrigatórios, CPF, critérios, dependentes e schema AUDFOBEN.
6. O gestor certifica a folha.
7. O próprio gestor gera e baixa o JSON.

Não existe mais o perfil `SECRETARIA_ENVIO`. O gestor concentra a certificação e geração do arquivo JSON.

## Perfis

| Perfil | Função |
|---|---|
| `ADMIN` | Administra usuários, Secretarias, UGs, exclusões administrativas e auditoria. |
| `SECRETARIA_OPERADOR` | Cadastra/importa/corrige beneficiários da própria Secretaria e solicita exclusão de beneficiário ao gestor. |
| `SECRETARIA_GESTOR` | Cadastra programas, cria folhas, valida, certifica, exclui beneficiários, gera JSON e solicita exclusão de folha ao ADM. |
| `SECRETARIA_CONSULTA` | Consulta os dados da própria Secretaria. |
| `CGM_CONSULTA` | Consulta/auditoria, sem aprovar, validar tecnicamente ou gerar remessa. |

## Principais mudanças da versão

- Remoção do perfil `SECRETARIA_ENVIO`.
- `SECRETARIA_GESTOR` passa a gerar JSON após certificação.
- Somente `ADMIN` cria Secretaria e Unidade Gestora.
- Somente `SECRETARIA_GESTOR` cria novos programas.
- Programa agora possui cadastro mais próximo da mecânica do e-TCERJ: forma de pagamento, populações atendidas, critérios vinculados, vigência e limites.
- Planilha Excel específica por programa, contendo os critérios selecionados no cadastro do programa.
- Remoção dos links de modelo CSV/Excel do menu lateral.
- Admin pode excluir/desativar usuários, Secretarias, UGs e folhas.
- Gestor pode solicitar exclusão de folha ao ADM.
- Gestor pode excluir beneficiários diretamente.
- Operador pode solicitar exclusão de beneficiário ao gestor.
- Criado painel de solicitações de exclusão.
- Mantida trilha de auditoria.

## Instalação no Windows

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Acesse:

```text
http://127.0.0.1:8000
```

Login inicial:

```text
Usuário: admin
Senha: Admin@12345
```

## Testes

```bash
pytest -q
```

Nesta versão, os testes automatizados foram executados com sucesso.

## Arquivos principais

| Arquivo | Função |
|---|---|
| `app/main.py` | Rotas, perfis, controle de acesso e telas. |
| `app/models.py` | Tabelas do banco de dados. |
| `app/services.py` | Importação, geração de planilhas, validação e exportação JSON. |
| `app/validators.py` | Validação de CPF, datas, critérios, dependentes e valores. |
| `app/catalogos.py` | Catálogos de critérios, formas de pagamento e populações atendidas. |
| `app/templates/*.html` | Telas do sistema. |
| `app/schema/audfoben.json` | Schema JSON AUDFOBEN. |

## Atenção sobre os critérios de elegibilidade

O catálogo em `app/catalogos.py` foi montado com base nas opções visíveis do módulo de Cadastro Auxiliar enviado. Antes de produção, a equipe deve conferir os identificadores finais com os códigos efetivamente gerados pelo e-TCERJ para cada programa cadastrado/homologado.

