from __future__ import annotations

import numpy as np
import pandas as pd

MISSING_TOKENS = {"*Em Branco", "Ignorado", "", "nan", "NaN", "None", "NoneType"}

DATE_COLS = [
    "DataNotificacao", "DataNascimento", "DataPrimeirosSintomas", "DataInvestigacao",
    "DataInternacao", "DataPuncaoLombar", "DataRealizacaoQuimioprofilaxiaComunicantes",
    "DataEvolucao", "DataEncerramento"
]

YES_VALUES = {"Sim", "SIM", "S", "1", 1, True}
NO_VALUES = {"Não", "Nao", "NÃO", "NAO", "N", "0", 0, False}


def normalize_missing(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if out[c].dtype == "object":
            out[c] = out[c].astype(str).str.strip()
            out[c] = out[c].replace(list(MISSING_TOKENS), np.nan)
    return out


def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in DATE_COLS:
        if c in out.columns:
            out[c] = pd.to_datetime(out[c], errors="coerce", dayfirst=True)
    return out


def normalize_strings(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Mantém acentos, mas remove espaços múltiplos.
    for c in out.select_dtypes(include=["object"]).columns:
        out[c] = out[c].astype(str).str.strip().replace({"nan": np.nan})
        out[c] = out[c].str.replace(r"\s+", " ", regex=True)
    return out


def sim_nao_to_binary(s: pd.Series) -> pd.Series:
    return s.map(lambda x: 1 if x in YES_VALUES else (0 if x in NO_VALUES else np.nan))


def clean_meningitis_data(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = out.columns.astype(str).str.replace("\ufeff", "", regex=False)
    out = normalize_missing(out)
    out = normalize_strings(out)
    out = parse_dates(out)

    for c in [
        "NumeroNotificacao", "CodigoMunicipioNotificacao", "CodigoMunicipioResidencia",
        "CodigoUnidadeNotificacao", "DiaSemanaNotificacao", "DiaSemanaPrimeirosSintomas",
        "NumeroCasos",
    ]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")

    if "IdadePaciente" in out.columns:
        # Exemplos: "010a", "036a"; extrai número.
        out["idade_anos"] = pd.to_numeric(out["IdadePaciente"].astype(str).str.extract(r"(\d+)")[0], errors="coerce")

    return out


def derive_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    event_date = out.get("DataPrimeirosSintomas")
    if event_date is None or event_date.isna().all():
        event_date = out.get("DataNotificacao")
    out["data_evento"] = event_date
    out["ano_evento"] = out["data_evento"].dt.year
    out["mes_evento"] = out["data_evento"].dt.month
    out["semana_epidemiologica"] = out["data_evento"].dt.isocalendar().week.astype("Int64")

    out["confirmado"] = out.get("ClassificacaoCaso", pd.Series(index=out.index)).eq("Confirmado").astype(int)
    out["descartado"] = out.get("ClassificacaoCaso", pd.Series(index=out.index)).eq("Descartado").astype(int)

    evol = out.get("EvolucaoCaso", pd.Series(index=out.index, dtype=object)).fillna("")
    out["obito_meningite"] = evol.str.contains("Óbito por meningite|Obito por meningite", case=False, regex=True).astype(int)
    out["obito_total"] = evol.str.contains("Óbito|Obito", case=False, regex=True).astype(int)

    if "OcorreuHospitalizacao" in out.columns:
        out["hospitalizado"] = sim_nao_to_binary(out["OcorreuHospitalizacao"]).fillna(0).astype(int)
    else:
        out["hospitalizado"] = np.nan

    lab_cols = [c for c in out.columns if c.startswith("Resultado")]
    if lab_cols:
        lab_non_missing = out[lab_cols].notna().any(axis=1)
        # Critério mais conservador: confirmação laboratorial por critério ou algum resultado informado.
        criterio = out.get("CriterioConfirmacao", pd.Series(index=out.index, dtype=object)).fillna("")
        out["confirmacao_laboratorial"] = (
            criterio.str.contains("Cultura|PCR|Bacterioscopia|Látex|Latex|Isolamento|CIE", case=False, regex=True)
            | lab_non_missing
        ).astype(int)
    else:
        out["confirmacao_laboratorial"] = np.nan

    # Tempos úteis.
    if {"DataPrimeirosSintomas", "DataNotificacao"}.issubset(out.columns):
        out["tempo_sintomas_notificacao_dias"] = (out["DataNotificacao"] - out["DataPrimeirosSintomas"]).dt.days
    if {"DataPrimeirosSintomas", "DataInternacao"}.issubset(out.columns):
        out["tempo_sintomas_internacao_dias"] = (out["DataInternacao"] - out["DataPrimeirosSintomas"]).dt.days
    if {"DataPrimeirosSintomas", "DataEvolucao"}.issubset(out.columns):
        out["tempo_sintomas_evolucao_dias"] = (out["DataEvolucao"] - out["DataPrimeirosSintomas"]).dt.days
    if {"DataNotificacao", "DataEncerramento"}.issubset(out.columns):
        out["tempo_notificacao_encerramento_dias"] = (out["DataEncerramento"] - out["DataNotificacao"]).dt.days

    # Indicadores binários para vacinação, comorbidades e sintomas.
    for prefix in ["Vacina", "DoencasPreexistentes", "SinaisESintomas"]:
        for c in [x for x in out.columns if x.startswith(prefix) and not x.endswith("Especificar")]:
            out[f"{c}_bin"] = sim_nao_to_binary(out[c])

    return out
