from __future__ import annotations

from pathlib import Path
from typing import Union, IO
import pandas as pd


def load_case_data(path_or_buffer: Union[str, Path, IO]) -> pd.DataFrame:
    """Carrega CSV detectando separador e encoding mais prováveis."""
    encodings = ["utf-8-sig", "utf-8", "latin1", "cp1252"]
    seps = [",", ";", "\t", "|"]
    last_error = None

    # Para objetos enviados pelo Streamlit, é necessário reposicionar o buffer.
    for enc in encodings:
        for sep in seps:
            try:
                if hasattr(path_or_buffer, "seek"):
                    path_or_buffer.seek(0)
                df = pd.read_csv(path_or_buffer, encoding=enc, sep=sep, low_memory=False)
                if df.shape[1] > 10:
                    df.columns = df.columns.astype(str).str.replace("\ufeff", "", regex=False)
                    return df
            except Exception as exc:  # pragma: no cover
                last_error = exc

    raise ValueError(f"Não foi possível ler o arquivo. Último erro: {last_error}")


def load_population(path: Union[str, Path]) -> pd.DataFrame:
    """Carrega população municipal.

    Espera, idealmente, colunas:
    - codigo_municipio
    - ano
    - populacao
    """
    pop = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
    rename = {}
    for c in pop.columns:
        lc = c.lower()
        if "cod" in lc and "mun" in lc:
            rename[c] = "codigo_municipio"
        elif lc in {"ano", "year"}:
            rename[c] = "ano"
        elif "pop" in lc:
            rename[c] = "populacao"
    pop = pop.rename(columns=rename)
    required = {"codigo_municipio", "ano", "populacao"}
    missing = required - set(pop.columns)
    if missing:
        raise ValueError(f"Arquivo de população sem colunas obrigatórias: {missing}")
    pop["codigo_municipio"] = pd.to_numeric(pop["codigo_municipio"], errors="coerce").astype("Int64")
    pop["ano"] = pd.to_numeric(pop["ano"], errors="coerce").astype("Int64")
    pop["populacao"] = pd.to_numeric(pop["populacao"], errors="coerce")
    return pop
