from __future__ import annotations

# Catálogos internos inspirados nas opções apresentadas pelo módulo de Cadastros Auxiliares do e-TCERJ.
# Os identificadores abaixo devem ser conferidos com o código efetivo atribuído pelo e-TCERJ no cadastro do programa.
# No município, o sistema usa estes códigos para vincular critérios ao programa e montar a planilha específica.

FORMAS_PAGAMENTO = [
    "Pagamento em reais",
    "Moeda Social",
    "Entrega de Produtos",
    "Cartões restritos a redes credenciadas",
]

POPULACOES_ATENDIDAS = [
    "Agricultor Familiar",
    "Agricultor Orgânico",
    "Artesão",
    "Beneficiário do Aluguel Social",
    "Dependente químico",
    "Desempregado",
    "Egresso do sistema prisional",
    "Gestante",
    "Idoso",
    "Mãe de bebê até 6 meses",
    "Mãe de criança e/ou adolescente (7 a 17 anos)",
    "Mãe de criança na Primeira Infância",
    "Microempreendedor Individual (MEI)",
    "Sócio de Microempresa (ME)",
    "Mulher",
    "Pescador Artesanal",
    "Pessoa com Deficiência",
    "Pessoa em situação de insegurança alimentar e nutricional",
    "Pessoa em situação de rua",
    "Pessoa em vulnerabilidade socioeconômica",
    "Pessoa LGBTQI+",
    "Pessoa na faixa de pobreza",
    "Pessoa na faixa de pobreza extrema",
    "Pessoa negra",
    "Povos e Comunidades Tradicionais",
    "Trabalhador autônomo",
    "Trabalhador informal",
    "Tutor de animal doméstico",
    "Vítima de calamidade pública/emergência",
    "Vítima de violência doméstica",
]

CRITERIOS_ELEGIBILIDADE = [
    {"id": 11, "nome": "Possuir inscrição no CadÚnico", "categoria": "Cadastro Social", "tipo_dado": "Sim/Não"},
    {"id": 12, "nome": "Estar com o CadÚnico atualizado no prazo próprio do município", "categoria": "Cadastro Social", "tipo_dado": "Sim/Não"},
    {"id": 13, "nome": "Possuir tempo mínimo de cadastro no CadÚnico", "categoria": "Cadastro Social", "tipo_dado": "Número"},
    {"id": 14, "nome": "Possuir cadastro no sistema municipal próprio", "categoria": "Cadastro Social", "tipo_dado": "Sim/Não"},
    {"id": 15, "nome": "Possuir identidade de pescador no ICMBio", "categoria": "Cadastro Social", "tipo_dado": "Sim/Não"},
    {"id": 16, "nome": "Estar inscrito no CadÚnico apenas nas faixas de pobreza ou pobreza extrema", "categoria": "Cadastro Social", "tipo_dado": "Sim/Não"},
    {"id": 17, "nome": "Ser maior de 18 anos ou emancipado", "categoria": "Cadastro Social", "tipo_dado": "Sim/Não"},
    {"id": 18, "nome": "Possuir cadastro no CAF (Cadastro Nacional da Agricultura Familiar)", "categoria": "Cadastro Social", "tipo_dado": "Sim/Não"},
    {"id": 19, "nome": "Receber até determinada renda per capita mensal", "categoria": "Renda", "tipo_dado": "Valor"},
    {"id": 20, "nome": "Receber até a renda familiar mensal", "categoria": "Renda", "tipo_dado": "Valor"},
    {"id": 21, "nome": "Não possuir renda formal", "categoria": "Renda", "tipo_dado": "Sim/Não"},
    {"id": 22, "nome": "Estar em situação de desemprego", "categoria": "Renda", "tipo_dado": "Sim/Não"},
    {"id": 23, "nome": "Não ser aposentado e/ou pensionista", "categoria": "Renda", "tipo_dado": "Sim/Não"},
    {"id": 24, "nome": "Não receber BPC", "categoria": "Renda", "tipo_dado": "Sim/Não"},
    {"id": 25, "nome": "Total de membros na família", "categoria": "Familiar", "tipo_dado": "Número"},
    {"id": 26, "nome": "Possuir criança ou adolescente na família", "categoria": "Familiar", "tipo_dado": "Sim/Não"},
    {"id": 27, "nome": "Possuir idoso na família", "categoria": "Familiar", "tipo_dado": "Sim/Não"},
    {"id": 28, "nome": "Possuir pessoa com deficiência na família", "categoria": "Familiar", "tipo_dado": "Sim/Não"},
    {"id": 29, "nome": "Número de filhos", "categoria": "Familiar", "tipo_dado": "Número"},
    {"id": 30, "nome": "Ser do sexo feminino", "categoria": "Sexo", "tipo_dado": "Sim/Não"},
    {"id": 31, "nome": "Estar em determinada faixa etária", "categoria": "Idade", "tipo_dado": "Número"},
    {"id": 32, "nome": "Residir atualmente no município instituidor do benefício", "categoria": "Residência", "tipo_dado": "Sim/Não"},
    {"id": 33, "nome": "Residir no município instituidor do benefício há número mínimo de anos", "categoria": "Residência", "tipo_dado": "Número"},
    {"id": 34, "nome": "Residir em área de vulnerabilidade", "categoria": "Residência", "tipo_dado": "Sim/Não"},
    {"id": 35, "nome": "Residir em área afetada por desastre", "categoria": "Residência", "tipo_dado": "Sim/Não"},
    {"id": 36, "nome": "Possuir laudo da Defesa Civil (residência afetada)", "categoria": "Residência", "tipo_dado": "Sim/Não"},
    {"id": 37, "nome": "Residir no Estado do Rio de Janeiro", "categoria": "Residência", "tipo_dado": "Sim/Não"},
    {"id": 38, "nome": "Não possuir financiamento imobiliário", "categoria": "Patrimônio", "tipo_dado": "Sim/Não"},
    {"id": 39, "nome": "Não possuir acomodações", "categoria": "Patrimônio", "tipo_dado": "Sim/Não"},
    {"id": 40, "nome": "Utilização do imóvel próprio como moradia própria permanente", "categoria": "Patrimônio", "tipo_dado": "Sim/Não"},
    {"id": 41, "nome": "Não possuir veículo", "categoria": "Patrimônio", "tipo_dado": "Sim/Não"},
    {"id": 42, "nome": "Possuir patrimônio total abaixo do valor determinado", "categoria": "Patrimônio", "tipo_dado": "Valor"},
    {"id": 43, "nome": "Não possuir vínculo de emprego formal", "categoria": "Trabalho", "tipo_dado": "Sim/Não"},
    {"id": 44, "nome": "Ser trabalhador informal", "categoria": "Trabalho", "tipo_dado": "Sim/Não"},
    {"id": 45, "nome": "Ser agricultor familiar", "categoria": "Trabalho", "tipo_dado": "Sim/Não"},
    {"id": 46, "nome": "Ser artesão", "categoria": "Trabalho", "tipo_dado": "Sim/Não"},
    {"id": 47, "nome": "Ser profissional liberal", "categoria": "Trabalho", "tipo_dado": "Sim/Não"},
    {"id": 48, "nome": "Ser pescador artesanal", "categoria": "Trabalho", "tipo_dado": "Sim/Não"},
    {"id": 49, "nome": "Ser agricultor orgânico", "categoria": "Trabalho", "tipo_dado": "Sim/Não"},
    {"id": 50, "nome": "Não ser servidor público", "categoria": "Trabalho", "tipo_dado": "Sim/Não"},
    {"id": 51, "nome": "Estar com os filhos matriculados regularmente (creches e escolas)", "categoria": "Educação", "tipo_dado": "Sim/Não"},
    {"id": 52, "nome": "Estar matriculado no curso de Ensino Superior", "categoria": "Educação", "tipo_dado": "Sim/Não"},
    {"id": 53, "nome": "Estar matriculado em curso técnico", "categoria": "Educação", "tipo_dado": "Sim/Não"},
    {"id": 54, "nome": "Estar com a carteira de vacinação em dia", "categoria": "Vacinação", "tipo_dado": "Sim/Não"},
    {"id": 55, "nome": "Estar com o acompanhamento pré-natal em dia", "categoria": "Gestante", "tipo_dado": "Sim/Não"},
    {"id": 56, "nome": "Ser pessoa com deficiência", "categoria": "PCD", "tipo_dado": "Sim/Não"},
    {"id": 57, "nome": "Ser brasileiro", "categoria": "Nacionalidade", "tipo_dado": "Sim/Não"},
    {"id": 58, "nome": "Não ser brasileiro", "categoria": "Nacionalidade", "tipo_dado": "Sim/Não"},
    {"id": 59, "nome": "Estar em situação de vulnerabilidade e risco social", "categoria": "Situação Social", "tipo_dado": "Sim/Não"},
    {"id": 60, "nome": "Ser vítima de violência doméstica", "categoria": "Situação Social", "tipo_dado": "Sim/Não"},
    {"id": 61, "nome": "Estar em situação de dependência química", "categoria": "Situação Social", "tipo_dado": "Sim/Não"},
    {"id": 62, "nome": "Estar em situação de rua", "categoria": "Situação Social", "tipo_dado": "Sim/Não"},
    {"id": 63, "nome": "Estar em situação de insegurança alimentar e nutricional", "categoria": "Situação Social", "tipo_dado": "Sim/Não"},
    {"id": 64, "nome": "Pertencer a Povos e Comunidades Tradicionais", "categoria": "Situação Social", "tipo_dado": "Sim/Não"},
    {"id": 65, "nome": "Ser egresso do sistema prisional", "categoria": "Situação Social", "tipo_dado": "Sim/Não"},
    {"id": 66, "nome": "Ser Microempreendedor Individual (MEI)", "categoria": "Empresário", "tipo_dado": "Sim/Não"},
    {"id": 67, "nome": "Ser Microempreendedor Individual (MEI) há um tempo mínimo", "categoria": "Empresário", "tipo_dado": "Número"},
    {"id": 68, "nome": "Ser Microempresário (ME)", "categoria": "Empresário", "tipo_dado": "Sim/Não"},
]


def criterio_por_id(criterio_id: int) -> dict | None:
    for criterio in CRITERIOS_ELEGIBILIDADE:
        if criterio["id"] == int(criterio_id):
            return criterio
    return None


def criterios_por_ids(ids: list[int | str]) -> list[dict]:
    result = []
    for raw in ids:
        if raw in (None, ""):
            continue
        criterio = criterio_por_id(int(raw))
        if criterio:
            result.append(criterio.copy())
    return result
