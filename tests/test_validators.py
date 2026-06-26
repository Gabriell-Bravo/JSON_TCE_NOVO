from app.validators import cpf_valido, validar_beneficiario_basico, validar_criterios, validar_dependentes


def test_cpf_valido():
    assert cpf_valido("529.982.247-25") is True
    assert cpf_valido("111.111.111-11") is False
    assert cpf_valido("52998224724") is False


def test_beneficiario_basico():
    data = {
        "cpf": "52998224725",
        "nome": "Maria da Silva",
        "sexo": "F",
        "dataNascimento": "1990-01-01",
        "nacionalidade": "Brasileira",
        "logradouro": "Rua A",
        "bairro": "Centro",
        "codigoIBGEMunicipio": "3305505",
    }
    assert validar_beneficiario_basico(data) == []


def test_criterios_exigem_aplicavel_s():
    criterios = [{"identificadorCriterio": 1, "valorAssociado": "Renda", "aplicavel": "N"}]
    assert any("aplicável" in msg for msg in validar_criterios(criterios))


def test_normalize_money_formats():
    from decimal import Decimal
    from app.validators import normalize_money
    assert normalize_money("450.00") == Decimal("450.00")
    assert normalize_money("1.234,56") == Decimal("1234.56")
    assert normalize_money("300,00") == Decimal("300.00")


def test_nacionalidade_adjetivo_detectado():
    from app.validators import nacionalidade_deve_ser_pais
    assert nacionalidade_deve_ser_pais("Brasil") is True
    assert nacionalidade_deve_ser_pais("Brasileira") is False


def test_dependente_maior_exige_cpf():
    deps = [{"nome":"João", "sexo":"M", "dataNascimento":"1990-01-01", "codigoParentesco":3}]
    assert any("CPF" in msg for msg in validar_dependentes(deps, 1))


def test_criterio_sim_nao_valor():
    from app.validators import validar_valor_associado_tipo
    assert validar_valor_associado_tipo("SIM", "Sim/Não") == []
    assert validar_valor_associado_tipo("talvez", "Sim/Não") != []


def test_criterio_vigencia_competencia():
    from app.validators import criterio_vigente_na_competencia, validar_criterios_do_programa
    meta = {"identificadorCriterio": 11, "tipoDado": "Sim/Não", "vigenciaInicio": "2026-01-01", "vigenciaFim": "2026-06-30", "prazoIndeterminado": False}
    assert criterio_vigente_na_competencia(meta, "2026", 3) is True
    assert criterio_vigente_na_competencia(meta, "2026", 8) is False
    erros = validar_criterios_do_programa(
        [{"identificadorCriterio": 11, "valorAssociado": "SIM", "aplicavel": "S"}],
        [meta],
        "2026",
        8,
    )
    assert any("vigente" in e for e in erros)
