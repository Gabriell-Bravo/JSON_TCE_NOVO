from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

CPF_RE = re.compile(r"^\d{11}$")
REPEATED_RE = re.compile(r"^(\d)\1{10}$")
IBGE_RE = re.compile(r"^\d{7}$")
NIS_RE = re.compile(r"^\d{11}$")
CEP_RE = re.compile(r"^\d{8}$")


def digits_only(value: Any) -> str:
    if value is None:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def cpf_valido(cpf: Any) -> bool:
    cpf = digits_only(cpf)
    if not CPF_RE.fullmatch(cpf):
        return False
    if REPEATED_RE.fullmatch(cpf):
        return False
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    d1 = 11 - (soma % 11)
    if d1 >= 10:
        d1 = 0
    if d1 != int(cpf[9]):
        return False
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    d2 = 11 - (soma % 11)
    if d2 >= 10:
        d2 = 0
    return d2 == int(cpf[10])


def normalize_date(value: Any) -> str:
    raw = clean_text(value)
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Data deve estar no formato AAAA-MM-DD.") from exc
    if parsed > date.today():
        raise ValueError("Data de nascimento não pode ser futura.")
    return parsed.isoformat()


def normalize_money(value: Any) -> float:
    raw = clean_text(value).replace("R$", "").replace(" ", "")
    if not raw:
        raise ValueError("Valor financeiro inválido.")
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        val = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("Valor financeiro inválido.") from exc
    if val < 0:
        raise ValueError("Valor financeiro não pode ser negativo.")
    if val.as_tuple().exponent < -2:
        raise ValueError("Valor financeiro deve ter no máximo duas casas decimais.")
    return float(val)


def parse_json_array(value: Any, field_name: str, required: bool = False) -> list[dict[str, Any]]:
    if value is None or clean_text(value) == "":
        if required:
            raise ValueError(f"{field_name} é obrigatório.")
        return []
    if isinstance(value, list):
        data = value
    else:
        try:
            data = json.loads(str(value))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{field_name} deve ser uma lista JSON válida: {exc}") from exc
    if not isinstance(data, list):
        raise ValueError(f"{field_name} deve ser uma lista JSON.")
    for item in data:
        if not isinstance(item, dict):
            raise ValueError(f"Cada item de {field_name} deve ser um objeto JSON.")
    return data


def validar_beneficiario_basico(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    cpf = digits_only(data.get("cpf"))
    if not cpf_valido(cpf):
        errors.append("CPF inválido: verifique os 11 dígitos e os dígitos verificadores.")
    nome = clean_text(data.get("nome"))
    if not nome or nome.lower() in {"não informado", "nao informado", "n/i", "ni"}:
        errors.append("Informe o nome completo do beneficiário (não use 'não informado' ou abreviações genéricas).")
    if clean_text(data.get("sexo")) not in {"M", "F"}:
        errors.append("Sexo deve ser M (masculino) ou F (feminino).")
    try:
        normalize_date(data.get("dataNascimento"))
    except ValueError as exc:
        errors.append(str(exc))
    nacionalidade = clean_text(data.get("nacionalidade"))
    if not nacionalidade or nacionalidade.lower() in {"não informado", "nao informado", "n/i", "ni"}:
        errors.append("Informe a nacionalidade (nome do país, por exemplo: Brasil).")
    logradouro = clean_text(data.get("logradouro"))
    if not logradouro or logradouro.lower() in {"não informado", "nao informado", "n/i", "ni"}:
        errors.append("Informe o logradouro (para situação de rua, use 'Pessoa em Situação de Rua').")
    bairro = clean_text(data.get("bairro"))
    if not bairro or bairro.lower() in {"não informado", "nao informado", "n/i", "ni"}:
        errors.append("Informe o bairro (para situação de rua, use 'Pessoa em Situação de Rua').")
    if not IBGE_RE.fullmatch(digits_only(data.get("codigoIBGEMunicipio"))):
        errors.append("Código IBGE do município deve ter exatamente 7 dígitos numéricos.")
    nis = digits_only(data.get("numeroNIS"))
    if nis and not NIS_RE.fullmatch(nis):
        errors.append("NIS, quando informado, deve ter 11 dígitos numéricos.")
    cep = digits_only(data.get("enderecoCEP"))
    if cep and not CEP_RE.fullmatch(cep):
        errors.append("CEP, quando informado, deve ter 8 dígitos numéricos.")
    return errors


def nacionalidade_deve_ser_pais(nacionalidade: str) -> bool:
    adjetivos = {"brasileira", "brasileiro", "estrangeira", "estrangeiro"}
    return clean_text(nacionalidade).lower() not in adjetivos


def validar_criterios(criterios: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if not criterios:
        return ["Informe ao menos um critério de elegibilidade para o beneficiário."]
    for idx, c in enumerate(criterios, 1):
        try:
            identificador = int(c.get("identificadorCriterio", 0))
        except Exception:
            identificador = 0
        if identificador < 1:
            errors.append(f"Critério {idx}: informe o código do critério cadastrado no e-TCERJ (mínimo 1).")
        if not clean_text(c.get("valorAssociado")):
            errors.append(f"Critério {idx}: informe o valor que comprova o atendimento ao critério.")
        if clean_text(c.get("aplicavel")) not in {"S", "N"}:
            errors.append(f"Critério {idx}: campo aplicável deve ser S (sim) ou N (não).")
    if not any(clean_text(c.get("aplicavel")) == "S" for c in criterios):
        errors.append("Ao menos um critério deve estar marcado como aplicável (S).")
    return errors


def calcular_idade(data_nascimento: str) -> int | None:
    try:
        born = datetime.strptime(data_nascimento, "%Y-%m-%d").date()
    except Exception:
        return None
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def validar_dependentes(dependentes: list[dict[str, Any]], total_dependentes: int) -> list[str]:
    errors: list[str] = []
    if total_dependentes != len(dependentes):
        errors.append("O total de dependentes informado não confere com a quantidade na lista de dependentes.")
    for idx, dep in enumerate(dependentes, 1):
        if not clean_text(dep.get("nome")):
            errors.append(f"Dependente {idx}: informe o nome completo.")
        if clean_text(dep.get("sexo")) not in {"M", "F"}:
            errors.append(f"Dependente {idx}: sexo deve ser M ou F.")
        try:
            nascimento = normalize_date(dep.get("dataNascimento"))
        except ValueError as exc:
            errors.append(f"Dependente {idx}: {exc}")
            nascimento = ""
        try:
            parentesco = int(dep.get("codigoParentesco", 0))
        except Exception:
            parentesco = 0
        if parentesco < 1 or parentesco > 11:
            errors.append(f"Dependente {idx}: código de parentesco deve ser de 1 a 11 (tabela CadÚnico).")
        cpf = digits_only(dep.get("cpf"))
        idade = calcular_idade(nascimento) if nascimento else None
        if cpf and not cpf_valido(cpf):
            errors.append(f"Dependente {idx}: CPF inválido.")
        if idade is not None and idade >= 18 and not cpf:
            errors.append(f"Dependente {idx}: CPF é obrigatório para dependente com 18 anos ou mais.")
    return errors


def gerar_criterio_unico(criterio_id: Any, criterio_valor: Any, criterio_aplicavel: Any) -> list[dict[str, Any]]:
    return [{
        "identificadorCriterio": int(criterio_id or 1),
        "valorAssociado": clean_text(criterio_valor) or "Critério informado pela Secretaria",
        "aplicavel": clean_text(criterio_aplicavel or "S").upper(),
    }]
