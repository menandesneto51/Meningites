# -*- coding: utf-8 -*-
"""
14_painel_epidemiologico_ms_v23.py
Painel epidemiológico estilo Informe MS / Caderno SINAN:
incidência, mortalidade e letalidade por etiologia, faixa etária e sexo.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from meningites_v17_common import OUT, MISSING, fmt_num, load_base_v17, text_key

# Faixas alinhadas ao Informe Meningites (CGVDI/DPNI/SVSA)
FAIXA_INFORME_ORDER = [
    "< 1 ano",
    "1 a 4 anos",
    "5 a 9 anos",
    "10 a 14 anos",
    "15 a 19 anos",
    "20 a 29 anos",
    "30 a 39 anos",
    "40 a 49 anos",
    "50 a 59 anos",
    "> 60 anos",
    "Ignorado/sem informação",
]

BACTERIANAS = {
    "Doença meningocócica",
    "Meningite tuberculosa",
    "Meningite bacteriana/outras bactérias",
    "Meningite por Hib/Hemófilo",
    "Meningite pneumocócica",
}


def map_faixa_informe(x) -> str:
    if pd.isna(x):
        return "Ignorado/sem informação"
    s = str(x).strip()
    if s.lower() in MISSING or s == "":
        return "Ignorado/sem informação"
    k = text_key(s)
    # Códigos/textos SINAN comuns
    if "MENOR" in k and "01" in k or k.startswith("00") or "<1" in s or "MENOR 1" in k or "MENOR DE 1" in k:
        return "< 1 ano"
    if "01 A 04" in k or "1 A 4" in k or k.startswith("01"):
        return "1 a 4 anos"
    if "05 A 09" in k or "5 A 9" in k or k.startswith("02"):
        return "5 a 9 anos"
    if "10 A 14" in k or k.startswith("03"):
        return "10 a 14 anos"
    if "15 A 19" in k or k.startswith("04"):
        return "15 a 19 anos"
    if any(t in k for t in ["20 A 24", "25 A 29"]) or k.startswith("05") or k.startswith("06"):
        return "20 a 29 anos"
    if any(t in k for t in ["30 A 34", "35 A 39"]) or k.startswith("07") or k.startswith("08"):
        return "30 a 39 anos"
    if any(t in k for t in ["40 A 44", "45 A 49"]) or k.startswith("09") or k.startswith("10"):
        return "40 a 49 anos"
    if any(t in k for t in ["50 A 54", "55 A 59"]) or k.startswith("11") or k.startswith("12"):
        return "50 a 59 anos"
    if any(t in k for t in ["60 A 64", "65", "60 E", "MAIS DE 60", "> 60"]) or k.startswith("13") or k.startswith("14"):
        return "> 60 anos"
    # Fallback por idade numérica se vier embutida
    age = pd.to_numeric(s, errors="coerce")
    if pd.notna(age):
        age = float(age)
        if age < 1:
            return "< 1 ano"
        if age <= 4:
            return "1 a 4 anos"
        if age <= 9:
            return "5 a 9 anos"
        if age <= 14:
            return "10 a 14 anos"
        if age <= 19:
            return "15 a 19 anos"
        if age <= 29:
            return "20 a 29 anos"
        if age <= 39:
            return "30 a 39 anos"
        if age <= 49:
            return "40 a 49 anos"
        if age <= 59:
            return "50 a 59 anos"
        return "> 60 anos"
    return "Ignorado/sem informação"


def map_sexo(x) -> str:
    if pd.isna(x):
        return "Ignorado"
    k = text_key(x)
    if k in {"1", "1 0", "M", "MASCULINO", "HOMEM"}:
        return "Masculino"
    if k in {"2", "2 0", "F", "FEMININO", "MULHER"}:
        return "Feminino"
    return "Ignorado"


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["ano_evento_v17"] = pd.to_numeric(d.get("ano_evento_v17"), errors="coerce")
    d["confirmado_v17"] = pd.to_numeric(d.get("confirmado_v17"), errors="coerce").fillna(0).astype(int)
    d["obito_meningite_v17"] = pd.to_numeric(d.get("obito_meningite_v17"), errors="coerce").fillna(0).astype(int)
    d["caso_v17"] = pd.to_numeric(d.get("caso_v17"), errors="coerce").fillna(1).astype(int)
    d["populacao_v17"] = pd.to_numeric(d.get("populacao_v17"), errors="coerce")
    d["classificacao_agrupada_v17"] = d.get("classificacao_agrupada_v17", "Ignorado/em branco").astype(str)
    d["faixa_informe_v23"] = d.get("FaixaEtaria", pd.Series(index=d.index)).map(map_faixa_informe)
    # Se IdadePaciente for parseável, reforça
    if "IdadePaciente" in d.columns:
        idade = pd.to_numeric(d["IdadePaciente"].astype(str).str.extract(r"(\d+[.,]?\d*)", expand=False).str.replace(",", "."), errors="coerce")
        miss = d["faixa_informe_v23"].eq("Ignorado/sem informação") & idade.notna()
        d.loc[miss, "faixa_informe_v23"] = idade.loc[miss].map(map_faixa_informe)
    d["sexo_padrao_v23"] = d.get("SexoPaciente", pd.Series(index=d.index)).map(map_sexo)
    d["grupo_etiologico_v23"] = np.where(
        d["classificacao_agrupada_v17"].isin(BACTERIANAS),
        "Meningite bacteriana",
        np.where(
            d["classificacao_agrupada_v17"].str.contains("viral|ass", case=False, na=False),
            "Meningite viral",
            d["classificacao_agrupada_v17"],
        ),
    )
    return d


def pop_por_ano(df: pd.DataFrame) -> pd.DataFrame:
    """População estadual = soma das populações municipais distintas no ano; carry-forward."""
    rows = []
    for ano, g in df.groupby("ano_evento_v17", dropna=True):
        mun = g.dropna(subset=["codigo_municipio_v17"]).drop_duplicates("codigo_municipio_v17")
        pop = pd.to_numeric(mun["populacao_v17"], errors="coerce").sum()
        rows.append({"ano_evento_v17": int(ano), "populacao_estado": pop if pop > 0 else np.nan})
    pop = pd.DataFrame(rows).sort_values("ano_evento_v17")
    # Carry-forward / backward para anos sem denominador (ex.: 2026)
    pop["populacao_estado"] = pop["populacao_estado"].ffill().bfill()
    pop["populacao_origem"] = "municipal_soma_com_carry"
    return pop


def rates(casos, obitos, pop):
    incidencia = casos / pop * 100000 if pd.notna(pop) and pop > 0 else np.nan
    mortalidade = obitos / pop * 100000 if pd.notna(pop) and pop > 0 else np.nan
    letalidade = obitos / casos * 100 if casos and casos > 0 else np.nan
    return incidencia, mortalidade, letalidade


def aggregate(df: pd.DataFrame, keys: list[str], pop_ano: pd.DataFrame, confirmed_only: bool = True) -> pd.DataFrame:
    d = df.copy()
    if confirmed_only:
        d = d[d["confirmado_v17"] == 1].copy()
    present = [k for k in keys if k in d.columns]
    if not present:
        return pd.DataFrame()
    g = d.groupby(present, dropna=False).agg(
        casos=("caso_v17", "sum"),
        confirmados=("confirmado_v17", "sum"),
        obitos_meningite=("obito_meningite_v17", "sum"),
    ).reset_index()
    if "ano_evento_v17" in g.columns:
        g = g.merge(pop_ano, on="ano_evento_v17", how="left")
    else:
        g["populacao_estado"] = pop_ano["populacao_estado"].iloc[-1] if len(pop_ano) else np.nan
    # Pop municipal quando disponível na agregação
    if "codigo_municipio_v17" in present:
        mun_pop = (
            df.dropna(subset=["codigo_municipio_v17"])
            .groupby(["ano_evento_v17", "codigo_municipio_v17"], dropna=False)["populacao_v17"]
            .max()
            .reset_index()
            .rename(columns={"populacao_v17": "populacao_municipio"})
        )
        # carry pop municipal por código
        mun_pop = mun_pop.sort_values(["codigo_municipio_v17", "ano_evento_v17"])
        mun_pop["populacao_municipio"] = mun_pop.groupby("codigo_municipio_v17")["populacao_municipio"].ffill().bfill()
        g = g.merge(mun_pop, on=["ano_evento_v17", "codigo_municipio_v17"], how="left")
        g["populacao_ref"] = g["populacao_municipio"].fillna(g["populacao_estado"])
    else:
        g["populacao_ref"] = g.get("populacao_estado", np.nan)

    inc, mort, let = [], [], []
    for _, r in g.iterrows():
        i, m, l = rates(r["casos"], r["obitos_meningite"], r["populacao_ref"])
        inc.append(i)
        mort.append(m)
        let.append(l)
    g["incidencia_100mil"] = inc
    g["mortalidade_100mil"] = mort
    g["letalidade_pct"] = let
    return g


def resumo_ano(df: pd.DataFrame, pop_ano: pd.DataFrame) -> pd.DataFrame:
    conf = df[df["confirmado_v17"] == 1]
    rows = []
    for ano, g in conf.groupby("ano_evento_v17", dropna=True):
        pop = pop_ano.loc[pop_ano["ano_evento_v17"] == ano, "populacao_estado"]
        popv = float(pop.iloc[0]) if len(pop) else np.nan
        casos = int(g["caso_v17"].sum())
        obitos = int(g["obito_meningite_v17"].sum())
        notif = int(df.loc[df["ano_evento_v17"] == ano, "caso_v17"].sum())
        i, m, l = rates(casos, obitos, popv)
        bact = g[g["classificacao_agrupada_v17"].isin(BACTERIANAS)]
        bi, bm, bl = rates(int(bact["caso_v17"].sum()), int(bact["obito_meningite_v17"].sum()), popv)
        rows.append({
            "ano_evento_v17": int(ano),
            "notificados": notif,
            "confirmados": casos,
            "obitos_meningite": obitos,
            "populacao_ref": popv,
            "incidencia_100mil": i,
            "mortalidade_100mil": m,
            "letalidade_pct": l,
            "confirmados_bacterianas": int(bact["caso_v17"].sum()),
            "obitos_bacterianas": int(bact["obito_meningite_v17"].sum()),
            "incidencia_bacteriana_100mil": bi,
            "mortalidade_bacteriana_100mil": bm,
            "letalidade_bacteriana_pct": bl,
            "pct_confirmacao": casos / notif * 100 if notif else np.nan,
        })
    return pd.DataFrame(rows).sort_values("ano_evento_v17")


def main():
    df0 = load_base_v17()
    if df0.empty:
        raise SystemExit("Base ausente.")
    df = prepare(df0)
    # Foco operacional: a partir de 2010 (série Informe) — mantém todos, mas marca
    pop_ano = pop_por_ano(df)

    resumo = resumo_ano(df, pop_ano)
    eti = aggregate(df, ["ano_evento_v17", "classificacao_agrupada_v17"], pop_ano, True)
    faixa = aggregate(df, ["ano_evento_v17", "faixa_informe_v23"], pop_ano, True)
    sexo = aggregate(df, ["ano_evento_v17", "sexo_padrao_v23"], pop_ano, True)
    eti_faixa = aggregate(df, ["ano_evento_v17", "classificacao_agrupada_v17", "faixa_informe_v23"], pop_ano, True)
    bact = aggregate(
        df[df["classificacao_agrupada_v17"].isin(BACTERIANAS)],
        ["ano_evento_v17", "classificacao_agrupada_v17"],
        pop_ano,
        True,
    )
    mun = aggregate(df, ["ano_evento_v17", "codigo_municipio_v17", "municipio_v17", "regional_v17"], pop_ano, True)
    grupo = aggregate(df, ["ano_evento_v17", "grupo_etiologico_v23"], pop_ano, True)

    # Ordenação de faixa
    if not faixa.empty:
        faixa["faixa_ordem"] = faixa["faixa_informe_v23"].map(
            {f: i for i, f in enumerate(FAIXA_INFORME_ORDER)}
        ).fillna(99)
        faixa = faixa.sort_values(["ano_evento_v17", "faixa_ordem"])

    # Último ano completo com população nativa (sem depender só de 2026 incompleto)
    anos_com_pop_nativa = (
        df.groupby("ano_evento_v17")["populacao_v17"]
        .apply(lambda s: pd.to_numeric(s, errors="coerce").fillna(0).gt(0).any())
    )
    anos_ok = [int(a) for a, ok in anos_com_pop_nativa.items() if ok and pd.notna(a)]
    ano_ref = max(anos_ok) if anos_ok else int(df["ano_evento_v17"].dropna().max())

    # Snapshot ano de referência (estilo Informe)
    snap_eti = eti[eti["ano_evento_v17"] == ano_ref].copy() if not eti.empty else pd.DataFrame()
    snap_faixa = faixa[faixa["ano_evento_v17"] == ano_ref].copy() if not faixa.empty else pd.DataFrame()
    snap_bact = bact[bact["ano_evento_v17"] == ano_ref].copy() if not bact.empty else pd.DataFrame()

    resumo.to_csv(OUT / "painel_epi_resumo_ano_v23.csv", index=False, encoding="utf-8-sig")
    eti.to_csv(OUT / "painel_epi_etiologia_ano_v23.csv", index=False, encoding="utf-8-sig")
    faixa.to_csv(OUT / "painel_epi_faixa_ano_v23.csv", index=False, encoding="utf-8-sig")
    sexo.to_csv(OUT / "painel_epi_sexo_ano_v23.csv", index=False, encoding="utf-8-sig")
    eti_faixa.to_csv(OUT / "painel_epi_etiologia_faixa_ano_v23.csv", index=False, encoding="utf-8-sig")
    bact.to_csv(OUT / "painel_epi_bacterianas_ano_v23.csv", index=False, encoding="utf-8-sig")
    mun.to_csv(OUT / "painel_epi_municipio_ano_v23.csv", index=False, encoding="utf-8-sig")
    grupo.to_csv(OUT / "painel_epi_grupo_ano_v23.csv", index=False, encoding="utf-8-sig")
    pop_ano.to_csv(OUT / "painel_epi_populacao_ano_v23.csv", index=False, encoding="utf-8-sig")
    snap_eti.to_csv(OUT / "painel_epi_snapshot_etiologia_v23.csv", index=False, encoding="utf-8-sig")
    snap_faixa.to_csv(OUT / "painel_epi_snapshot_faixa_v23.csv", index=False, encoding="utf-8-sig")
    snap_bact.to_csv(OUT / "painel_epi_snapshot_bacterianas_v23.csv", index=False, encoding="utf-8-sig")

    meta = pd.DataFrame([{
        "ano_referencia": ano_ref,
        "fonte": "SINAN (base única V17) + população municipal; carry-forward quando ano sem pop",
        "denominador": "casos confirmados para incidência/mortalidade/letalidade (Caderno SINAN / Informe MS)",
        "interpretacao": (
            f"Ano de referência do snapshot: {ano_ref}. "
            f"Incidência {fmt_num(resumo.loc[resumo['ano_evento_v17']==ano_ref,'incidencia_100mil'].iloc[0]) if ano_ref in set(resumo['ano_evento_v17']) else 'NA'} "
            f"por 100 mil; letalidade {fmt_num(resumo.loc[resumo['ano_evento_v17']==ano_ref,'letalidade_pct'].iloc[0]) if ano_ref in set(resumo['ano_evento_v17']) else 'NA'}%."
        ),
    }])
    meta.to_csv(OUT / "painel_epi_meta_v23.csv", index=False, encoding="utf-8-sig")

    print("[OK] Painel epidemiológico MS V23 gerado.")
    print(f"Ano referência snapshot: {ano_ref}")
    if not resumo.empty:
        print(resumo.tail(6).to_string(index=False))


if __name__ == "__main__":
    main()
