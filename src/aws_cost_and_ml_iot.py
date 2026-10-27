"""Fase 5 — Comparativo de Custos AWS (us-east-1 vs sa-east-1) e Boas Práticas de ML com IoT.

Uso pela linha de comando:

    python -m src.aws_cost_and_ml_iot --demo
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
DATA_DIR = PROJECT_ROOT / "data"

# Estimativa mensal AWS Pricing Calculator (On-Demand, USD/mês) para a pilha FarmTech:
# EC2 t3.medium (Linux, 2 vCPU, 4 GB RAM, 730h) + EBS gp3 50 GB + S3 Standard 100 GB +
# RDS/DB t3.micro (Single-AZ, 20 GB) + AWS IoT Core (500k msgs) + Amazon SNS (10k notificações)
AWS_PRICING_USD = [
    {"servico": "EC2 t3.medium (730h + 50GB gp3)", "us_east_1_virginia": 34.41, "sa_east_1_sao_paulo": 54.12},
    {"servico": "RDS / DB t3.micro (20GB gp3)", "us_east_1_virginia": 18.25, "sa_east_1_sao_paulo": 29.80},
    {"servico": "Amazon S3 Standard (100 GB)", "us_east_1_virginia": 2.30, "sa_east_1_sao_paulo": 4.05},
    {"servico": "AWS IoT Core + SNS + Tráfego", "us_east_1_virginia": 3.50, "sa_east_1_sao_paulo": 5.20},
]


def calcular_comparativo_custos(cotacao_brl: float = 5.10) -> dict:
    """Compara os custos mensais e anuais entre N. Virginia (us-east-1) e São Paulo (sa-east-1)."""
    df = pd.DataFrame(AWS_PRICING_USD)
    df["economia_usd_mes"] = (df["sa_east_1_sao_paulo"] - df["us_east_1_virginia"]).round(2)
    df["diferenca_pct"] = ((df["sa_east_1_sao_paulo"] / df["us_east_1_virginia"] - 1.0) * 100.0).round(1)

    total_us = round(float(df["us_east_1_virginia"].sum()), 2)
    total_sa = round(float(df["sa_east_1_sao_paulo"].sum()), 2)
    economia_mensal_usd = round(total_sa - total_us, 2)
    economia_pct = round((1.0 - total_us / total_sa) * 100.0, 1)

    return {
        "itens": df.to_dict(orient="records"),
        "total_mensal_us_east_1_usd": total_us,
        "total_mensal_sa_east_1_usd": total_sa,
        "total_anual_us_east_1_usd": round(total_us * 12, 2),
        "total_anual_sa_east_1_usd": round(total_sa * 12, 2),
        "total_mensal_us_east_1_brl": round(total_us * cotacao_brl, 2),
        "total_mensal_sa_east_1_brl": round(total_sa * cotacao_brl, 2),
        "economia_mensal_usd": economia_mensal_usd,
        "economia_pct_us_vs_sa": economia_pct,
        "regiao_recomendada_custo": "us-east-1 (N. Virginia)",
        "regiao_recomendada_lgpd_latencia": "sa-east-1 (São Paulo)",
    }


def detectar_anomalias_iot(n_leituras: int = 150, seed: int = 42) -> dict:
    """Aplica boas práticas de ML em IoT: filtragem de falhas de sensor (outliers) com IsolationForest."""
    rng = np.random.default_rng(seed)
    umidade_normal = rng.normal(48.0, 6.5, size=n_leituras - 6)
    temp_normal = rng.normal(24.5, 2.2, size=n_leituras - 6)
    ph_normal = rng.normal(5.9, 0.25, size=n_leituras - 6)

    # 6 leituras corrompidas por ruído elétrico / cabo oxidado no campo
    umidade_esp = np.array([0.0, 99.9, 105.0, -4.0, 98.5, 1.2])
    temp_esp = np.array([85.0, -10.0, 72.0, 68.0, -5.0, 91.0])
    ph_esp = np.array([1.1, 13.5, 0.5, 12.8, 1.8, 13.1])

    df = pd.DataFrame({
        "umidade_solo_pct": np.concatenate([umidade_normal, umidade_esp]).round(2),
        "temperatura_c": np.concatenate([temp_normal, temp_esp]).round(2),
        "ph_solo": np.concatenate([ph_normal, ph_esp]).round(2),
        "falha_sensor_real": np.array([0] * (n_leituras - 6) + [1] * 6),
    })

    iso = IsolationForest(contamination=0.05, random_state=seed)
    pred = iso.fit_predict(df[["umidade_solo_pct", "temperatura_c", "ph_solo"]])
    df["anomalia_detectada"] = (pred == -1).astype(int)

    tp = int(((df["falha_sensor_real"] == 1) & (df["anomalia_detectada"] == 1)).sum())
    return {
        "total_leituras": int(len(df)),
        "anomalias_reais": 6,
        "anomalias_detectadas": int(df["anomalia_detectada"].sum()),
        "falhas_sensor_capturadas": tp,
        "taxa_captura_falhas": round(tp / 6.0, 4),
        "dataframe": df,
    }


def gerar_diagrama_arquitetura_aws(out_path: Path | None = None) -> Path:
    """Desenha a arquitetura em nuvem AWS da FarmTech Solutions."""
    if out_path is None:
        out_path = ASSETS_DIR / "arquitetura_aws_fase5.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(11.5, 5.4))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis("off")
    ax.set_title(
        "Arquitetura em Nuvem AWS — FarmTech Solutions (Fase 5 & Integração Fase 7)",
        fontsize=12.5, fontweight="bold", color="#1B365D",
    )

    blocos = [
        (0.4, 2.0, 2.3, 2.2, "Campo / Lavoura\n(Borda IoT)", [
            "ESP32 + DHT22 + NPK",
            "Câmeras nos Talhões",
            "Protocolo MQTT / TLS",
        ], "#E8F5E9"),
        (3.4, 3.2, 2.5, 2.0, "Ingestão & Armazenamento", [
            "AWS IoT Core",
            "Amazon S3 Data Lake",
            "(SSE-S3 Criptografado)",
        ], "#E3F2FD"),
        (3.4, 0.6, 2.5, 2.0, "Banco Relacional", [
            "Amazon RDS (Oracle/SQL)",
            "Subnet Privada VPC",
            "Tabelas Fase 3",
        ], "#FFF8E1"),
        (6.6, 1.9, 2.5, 2.3, "Processamento & IA\n(Amazon EC2 t3.medium)", [
            "Sanitização IoT (IsoForest)",
            "Modelos Scikit-Learn (F4)",
            "Visão YOLO (F6) + Dashboard",
        ], "#F3E5F5"),
        (9.6, 1.9, 2.1, 2.3, "Mensageria & Alertas\n(Amazon SNS / SES)", [
            "Tópico: alertas-lavoura",
            "E-mail + SMS Agrônomo",
            "IAM Least Privilege",
        ], "#FDECEA"),
    ]

    for x, y, w, h, titulo, linhas, cor in blocos:
        box = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08", facecolor=cor, edgecolor="#1B365D", lw=1.6)
        ax.add_patch(box)
        ax.text(x + w / 2, y + h - 0.35, titulo, ha="center", va="center", fontsize=9.5, fontweight="bold", color="#1B365D")
        for i, linha in enumerate(linhas):
            ax.text(x + w / 2, y + h - 0.85 - i * 0.36, linha, ha="center", va="center", fontsize=8.3)

    setas = [
        ((2.7, 3.5), (3.4, 4.1)),
        ((2.7, 2.6), (3.4, 1.7)),
        ((5.9, 4.1), (6.6, 3.3)),
        ((5.9, 1.7), (6.6, 2.6)),
        ((9.1, 3.0), (9.6, 3.0)),
    ]
    for p0, p1 in setas:
        ax.annotate("", xy=p1, xytext=p0, arrowprops=dict(arrowstyle="->", lw=1.8, color="#0D47A1"))

    fig.tight_layout()
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return out_path


def gerar_grafico_custos_e_iot(custos: dict, iot: dict, out_path: Path | None = None) -> Path:
    """Gera figura comparando custos us-east-1 vs sa-east-1 e detecção de anomalias IoT."""
    if out_path is None:
        out_path = ASSETS_DIR / "comparativo_aws_fase5.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df_c = pd.DataFrame(custos["itens"])
    df_iot = iot["dataframe"]

    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.7))

    ax = axes[0]
    idx = np.arange(len(df_c))
    ax.barh(idx - 0.18, df_c["us_east_1_virginia"], height=0.35, color="#1565C0", label=f"us-east-1 (Total US$ {custos['total_mensal_us_east_1_usd']}/mês)")
    ax.barh(idx + 0.18, df_c["sa_east_1_sao_paulo"], height=0.35, color="#EF6C00", label=f"sa-east-1 (Total US$ {custos['total_mensal_sa_east_1_usd']}/mês)")
    ax.set_yticks(idx, df_c["servico"])
    ax.set_xlabel("Custo Mensal On-Demand [USD]")
    ax.set_title(f"Calculadora AWS: Economia de {custos['economia_pct_us_vs_sa']}% em us-east-1")
    ax.grid(alpha=0.3, axis="x")
    ax.legend(fontsize=8.5)

    ax2 = axes[1]
    norm = df_iot[df_iot["anomalia_detectada"] == 0]
    anom = df_iot[df_iot["anomalia_detectada"] == 1]
    ax2.scatter(norm["umidade_solo_pct"], norm["temperatura_c"], color="#2E7D32", alpha=0.75, s=36, label="Leitura válida IoT")
    ax2.scatter(anom["umidade_solo_pct"], anom["temperatura_c"], color="#C62828", marker="x", s=75, lw=2, label="Anomalia bloqueada (IsolationForest)")
    ax2.set_xlabel("Umidade lida pelo sensor [%]")
    ax2.set_ylabel("Temperatura lida [°C]")
    ax2.set_title("Boas Práticas ML + IoT: Filtragem de Leituras Corrompidas")
    ax2.grid(alpha=0.3)
    ax2.legend(fontsize=8.5)

    fig.tight_layout()
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return out_path


def executar_analise_fase5() -> dict:
    custos = calcular_comparativo_custos()
    iot = detectar_anomalias_iot()
    arq_png = gerar_diagrama_arquitetura_aws()
    comp_png = gerar_grafico_custos_e_iot(custos, iot)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    resumo = {
        "custos_aws": custos,
        "qualidade_iot": {k: v for k, v in iot.items() if k != "dataframe"},
        "arquitetura_png": str(arq_png),
        "comparativo_png": str(comp_png),
    }
    (DATA_DIR / "resumo_aws_fase5.json").write_text(
        json.dumps(resumo, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return resumo


def main() -> None:
    parser = argparse.ArgumentParser(description="Fase 5 — Custos, Segurança AWS e ML com IoT")
    parser.add_argument("--demo", action="store_true", help="Executa a análise completa da Fase 5")
    parser.parse_args()

    res = executar_analise_fase5()
    c = res["custos_aws"]
    q = res["qualidade_iot"]
    print("=== FASE 5 — INFRAESTRUTURA AWS & BOAS PRÁTICAS DE ML COM IOT ===")
    print(f"Custo mensal us-east-1 (N. Virginia): US$ {c['total_mensal_us_east_1_usd']} (R$ {c['total_mensal_us_east_1_brl']})")
    print(f"Custo mensal sa-east-1 (São Paulo)  : US$ {c['total_mensal_sa_east_1_usd']} (R$ {c['total_mensal_sa_east_1_brl']})")
    print(f"Economia escolhendo us-east-1       : US$ {c['economia_mensal_usd']}/mês ({c['economia_pct_us_vs_sa']}%)")
    print(f"Sanitização IoT (IsolationForest)   : {q['falhas_sensor_capturadas']}/{q['anomalias_reais']} falhas elétricas bloqueadas antes do ML")


if __name__ == "__main__":
    main()
