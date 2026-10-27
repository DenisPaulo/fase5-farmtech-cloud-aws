"""Testes automatizados da Fase 5 (Custos AWS, CloudFormation/IAM e ML com IoT)."""

from pathlib import Path

from src.aws_cost_and_ml_iot import (
    PROJECT_ROOT,
    calcular_comparativo_custos,
    detectar_anomalias_iot,
    executar_analise_fase5,
)


def test_comparativo_custos_virginia_mais_barata_que_sp():
    c = calcular_comparativo_custos()
    assert c["total_mensal_us_east_1_usd"] < c["total_mensal_sa_east_1_usd"]
    assert c["economia_pct_us_vs_sa"] > 30.0


def test_deteccao_anomalias_iot_captura_sensores_corrompidos():
    iot = detectar_anomalias_iot()
    assert iot["falhas_sensor_capturadas"] >= 5
    assert iot["taxa_captura_falhas"] >= 0.80


def test_arquivos_cloudformation_iam_e_figuras():
    res = executar_analise_fase5()
    assert Path(res["arquitetura_png"]).exists()
    assert Path(res["comparativo_png"]).exists()
    assert (PROJECT_ROOT / "aws" / "cloudformation_farmtech.yaml").exists()
    assert (PROJECT_ROOT / "aws" / "iam_least_privilege_policy.json").exists()
