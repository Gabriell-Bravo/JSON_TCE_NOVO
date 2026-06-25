from __future__ import annotations

STATUS_LABELS = {
    "RASCUNHO": "Em elaboração",
    "PENDENTE": "Com pendências",
    "VALIDADA": "Validada",
    "CERTIFICADA_GESTOR": "Certificada pelo gestor",
    "GERADA": "JSON gerado",
}

ISSUE_LABELS = {
    "PROGRAMA_SEM_CODIGO_ETCE": "Programa sem código no e-TCERJ",
    "PROGRAMA_NAO_HOMOLOGADO": "Programa não homologado no e-TCERJ",
    "PROGRAMA_NAO_VIGENTE": "Programa fora de vigência",
    "FOLHA_SEM_ITENS": "Folha sem beneficiários",
    "CPF_DUPLICADO_FOLHA": "CPF repetido na folha",
    "CPF_INVALIDO": "CPF com dígitos verificadores inválidos",
    "BENEFICIARIO_INVALIDO": "Dados do beneficiário incompletos ou inválidos",
    "CRITERIO_INVALIDO": "Critério de elegibilidade inválido",
    "DEPENDENTE_INVALIDO": "Dados de dependente inválidos",
    "TOTAL_PESSOAS_INCOERENTE": "Total de pessoas não confere com dependentes",
    "FOLHA_SUPLEMENTAR_SEM_ORDINARIA": "Folha suplementar sem folha ordinária na competência",
    "ANO_REFERENCIA_ANTIGO": "Ano de referência anterior a 2026",
    "NACIONALIDADE_ADJETIVO": "Nacionalidade deve ser o nome do país",
    "SEM_EVIDENCIA": "Sem referência de processo ou evidência",
    "JSON_SCHEMA": "Arquivo JSON fora do padrão AUDFOBEN",
}


def mask_cpf(cpf: str, masked: bool = True) -> str:
    digits = "".join(ch for ch in str(cpf or "") if ch.isdigit())
    if not masked or len(digits) != 11:
        return digits
    return f"{digits[:3]}.***.***-{digits[-2:]}"


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def issue_label(code: str) -> str:
    return ISSUE_LABELS.get(code, code)
