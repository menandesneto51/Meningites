from __future__ import annotations

import pandas as pd


def merge_environmental(df: pd.DataFrame, environmental_csv: str) -> pd.DataFrame:
    """Integra temperatura, umidade e precipitação por data e município.

    Espera colunas:
    - data
    - codigo_municipio
    - temperatura
    - umidade
    - precipitacao
    """
    env = pd.read_csv(environmental_csv, sep=None, engine="python", encoding="utf-8-sig")
    env = env.rename(columns={
        "Data": "data", "DATA": "data",
        "CodigoMunicipio": "codigo_municipio", "cod_mun": "codigo_municipio",
        "Temperatura": "temperatura", "Umidade": "umidade", "Precipitacao": "precipitacao",
        "Precipitação": "precipitacao",
    })
    env["data"] = pd.to_datetime(env["data"], errors="coerce", dayfirst=True)
    env["codigo_municipio"] = pd.to_numeric(env["codigo_municipio"], errors="coerce").astype("Int64")

    out = df.copy()
    out["codigo_municipio_join"] = pd.to_numeric(out["CodigoMunicipioResidencia"], errors="coerce").astype("Int64")
    return out.merge(
        env,
        how="left",
        left_on=["data_evento", "codigo_municipio_join"],
        right_on=["data", "codigo_municipio"],
    )
