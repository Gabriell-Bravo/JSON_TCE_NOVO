# Plano de alterações para Cursor/Codex

## Objetivo
Revisar e melhorar o sistema sem alterar o fluxo definido: Secretaria gestora cadastra/importa, gestor certifica e o próprio gestor gera o JSON. Não incluir Finanças nem validação técnica obrigatória da CGM.

## Regras implementadas

1. Remover perfil `SECRETARIA_ENVIO`.
2. `SECRETARIA_GESTOR` gera o JSON.
3. Só `ADMIN` cria Secretaria e UG.
4. Só `SECRETARIA_GESTOR` cria programa.
5. Admin pode excluir/desativar entidades administrativas.
6. Gestor pode solicitar exclusão de folha ao ADM.
7. Gestor pode excluir beneficiário manualmente.
8. Operador pode solicitar exclusão de beneficiário ao gestor.
9. Cadastro de programa vincula critérios predeterminados.
10. Geração de planilha Excel específica por programa.
11. Remoção dos links de planilha do menu lateral.

## Pontos para revisão futura

- Conferir catálogo final de critérios e códigos efetivos do e-TCERJ.
- Migrar SQLite para PostgreSQL antes de produção.
- Implementar autenticação institucional.
- Implementar backup automático e HTTPS.
- Criar tela de edição de programa.
- Criar tela para edição individual de beneficiário.
- Criar campo de protocolo/recibo do e-TCERJ após envio real.

