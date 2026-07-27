from __future__ import annotations

import pandas as pd
import numpy as np


def build_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for c in df.columns:
        rows.append({
            "variavel": c,
            "tipo": str(df[c].dtype),
            "n": len(df),
            "preenchidos": int(df[c].notna().sum()),
            "faltantes": int(df[c].isna().sum()),
            "perc_faltante": round(float(df[c].isna().mean() * 100), 2),
            "valores_unicos": int(df[c].nunique(dropna=True)),
        })
    return pd.DataFrame(rows).sort_values("perc_faltante", ascending=False)


def logical_consistency_report(df: pd.DataFrame) -> pd.DataFrame:
    checks = []

    def add_check(name: str, mask: pd.Series, severity: str, description: str):
        checks.append({
            "regra": name,
            "n_inconsistencias": int(mask.fillna(False).sum()),
            "percentual": round(float(mask.fillna(False).mean() * 100), 3),
            "gravidade": severity,
            "descricao": description,
        })

    pairs = [
        ("sintomas_depois_notificacao", "DataPrimeirosSintomas", "DataNotificacao", "Data de sintomas posterior à notificação"),
        ("notificacao_depois_investigacao", "DataNotificacao", "DataInvestigacao", "Investigação anterior à notificação"),
        ("sintomas_depois_internacao", "DataPrimeirosSintomas", "DataInternacao", "Internação anterior aos sintomas"),
        ("sintomas_depois_puncao", "DataPrimeirosSintomas", "DataPuncaoLombar", "Punção anterior aos sintomas"),
        ("sintomas_depois_evolucao", "DataPrimeirosSintomas", "DataEvolucao", "Evolução anterior aos sintomas"),
        ("notificacao_depois_encerramento", "DataNotificacao", "DataEncerramento", "Encerramento anterior à notificação"),
    ]
    for name, early, late, desc in pairs:
        if early in df.columns and late in df.columns:
            mask = df[early].notna() & df[late].notna() & (df[early] > df[late])
            add_check(name, mask, "alta", desc)

    if {"SexoPaciente", "Gestante"}.issubset(df.columns):
        mask = df["SexoPaciente"].isin(["M", "I"]) & df["Gestante"].notna() & ~df["Gestante"].isin(["Não se aplica", "Nao se aplica"])
        add_check("sexo_vs_gestante", mask, "media", "Sexo masculino/ignorado com campo gestante incompatível")

    if "NumeroNotificacao" in df.columns:
        mask = df["NumeroNotificacao"].duplicated(keep=False)
        add_check("numero_notificacao_duplicado", mask, "alta", "Número de notificação repetido")

    if {"DataNascimento", "DataPrimeirosSintomas"}.issubset(df.columns):
        mask = df["DataNascimento"].notna() & df["DataPrimeirosSintomas"].notna() & (df["DataNascimento"] > df["DataPrimeirosSintomas"])
        add_check("nascimento_depois_sintomas", mask, "alta", "Data de nascimento posterior aos sintomas")

    return pd.DataFrame(checks)


def validity_vpp_report(df: pd.DataFrame) -> pd.DataFrame:
    """VPP sindrômico-laboratorial: entre confirmados/suspeitos, quanto tem confirmação laboratorial."""
    if "confirmado" not in df.columns or "confirmacao_laboratorial" not in df.columns:
        return pd.DataFrame()

    confirmed = df["confirmado"].eq(1)
    lab = df["confirmacao_laboratorial"].eq(1)
    total_confirmed = int(confirmed.sum())
    true_lab = int((confirmed & lab).sum())

    vpp = true_lab / total_confirmed if total_confirmed else np.nan

    rows = [{
        "indicador": "VPP_confirmado_laboratorial",
        "numerador": true_lab,
        "denominador": total_confirmed,
        "valor": vpp,
        "interpretacao": "Proporção de casos classificados como confirmados com evidência laboratorial registrada.",
    }]

    if "ClassificacaoMeningite" in df.columns:
        by_class = (
            df.assign(confirmado_lab=confirmed & lab)
            .groupby("ClassificacaoMeningite", dropna=False)
            .agg(n_confirmados=("confirmado", "sum"), n_lab=("confirmacao_laboratorial", "sum"))
            .reset_index()
        )
        by_class["vpp_aproximado"] = by_class["n_lab"] / by_class["n_confirmados"].replace(0, np.nan)
        by_class["indicador"] = "VPP_por_classificacao"
        rows.extend(by_class.to_dict("records"))

    return pd.DataFrame(rows)
