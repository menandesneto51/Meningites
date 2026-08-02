# -*- coding: utf-8 -*-
"""
28_indicadores_novos_v28.py
Indicadores novos de vigilância das meningites (CIEVS-MT):
oportunidade de coleta liquórica, tempo até quimioprofilaxia, cobertura de
sorogrupo em DM confirmada, contatos por caso de DM, subnotificação de
mortalidade (SIM×SINAN), oportunidade de detecção, casos sem denominador
populacional, completude dos campos essenciais e letalidade padronizada
por idade. Opcional: varredura espaço-temporal de DM.
"""

from __future__ import annotations

import importlib
from datetime import datetime

import numpy as np
import pandas as pd

from meningites_v17_common import MISSING, OUT, REL, fmt_num, load_base_v17, text_key

ms = importlib.import_module("12_indicadores_ms_operacionais_v23")
epi = importlib.import_module("14_painel_epidemiologico_ms_v23")
qual = importlib.import_module("11_qualidade_score_v20")

DM = "Doença meningocócica"
DM_HIB = ms.DM_HIB
CAMPOS_ESSENCIAIS = list(qual.CRITICAL_FIELDS)
FAIXA_ORDER = list(epi.FAIXA_INFORME_ORDER)

# Códigos/textos que não contam como sorogrupo informado
SORO_VAZIO = {"", "IGNORADO", "IGNORADO SEM INFORMACAO", "NAO INFORMADO", "SEM INFORMACAO", "9", "99"}

ESCOPO_ESTADUAL = "MATO GROSSO"


# ── Utilitários ──────────────────────────────────────────────────────────────

def _pct(num, den):
    """Proporção com proteção contra denominador zero/ausente."""
    if den is None or pd.isna(den) or float(den) == 0:
        return np.nan
    return float(num) / float(den) * 100


def _num(d: pd.DataFrame, col: str) -> pd.Series:
    if col not in d.columns:
        return pd.Series(np.nan, index=d.index, dtype="float64")
    return pd.to_numeric(d[col], errors="coerce")


def _dates(d: pd.DataFrame, col: str) -> pd.Series:
    if col not in d.columns:
        return pd.Series(pd.NaT, index=d.index)
    return pd.to_datetime(d[col], errors="coerce")


def _filled(s: pd.Series) -> pd.Series:
    return s.notna() & ~s.astype(str).str.strip().str.lower().isin(MISSING)


def _p(s: pd.Series, q: float):
    s = s.dropna()
    if s.empty:
        return np.nan
    return float(s.quantile(q))


def _clas(d: pd.DataFrame) -> pd.Series:
    if "classificacao_agrupada_v17" not in d.columns:
        return pd.Series("Ignorado/em branco", index=d.index, dtype=object)
    return d["classificacao_agrupada_v17"].astype(str)


def _soro_col(d: pd.DataFrame) -> str | None:
    return next((c for c in d.columns if "sorogrupo" in c.lower() or "SeNMeningiditis" in c), None)


def _iter_escopos(d: pd.DataFrame, incluir_ano: bool = True):
    """Estadual + por regional + (opcional) por ano do evento."""
    yield "ESTADUAL", ESCOPO_ESTADUAL, d
    if "regional_v17" in d.columns:
        reg = d["regional_v17"].fillna("Sem regional").astype(str)
        for nome, g in d.groupby(reg, dropna=False):
            yield "REGIONAL", str(nome), g
    if incluir_ano and "ano_evento_v17" in d.columns:
        anos = pd.to_numeric(d["ano_evento_v17"], errors="coerce")
        for ano, g in d.groupby(anos, dropna=True):
            yield "ANO", str(int(ano)), g


def _por_escopo(d: pd.DataFrame, calc, incluir_ano: bool = True) -> pd.DataFrame:
    rows = []
    for escopo, recorte, g in _iter_escopos(d, incluir_ano):
        row = {"escopo": escopo, "recorte": recorte}
        row.update(calc(g))
        rows.append(row)
    return pd.DataFrame(rows)


def _to_long(wide: pd.DataFrame, spec: dict, familia: str) -> list[dict]:
    """spec: coluna_valor -> (nome_indicador, unidade, col_numerador, col_denominador)."""
    rows = []
    if wide is None or wide.empty:
        return rows
    for _, r in wide.iterrows():
        for col, (nome, unidade, ncol, dcol) in spec.items():
            if col not in wide.columns:
                continue
            rows.append({
                "familia": familia,
                "indicador": nome,
                "escopo": r.get("escopo"),
                "recorte": r.get("recorte"),
                "valor": r.get(col),
                "numerador": r.get(ncol) if ncol else np.nan,
                "denominador": r.get(dcol) if dcol else np.nan,
                "unidade": unidade,
            })
    return rows


# ── 1. Oportunidade de coleta liquórica ──────────────────────────────────────

def calc_coleta_liquorica(d: pd.DataFrame) -> dict:
    """% de coleta de líquor ≤1 e ≤2 dias do início dos sintomas, mediana e P90.

    Restrito aos casos com data de punção lombar preenchida.
    """
    lt = _num(d, "lt_sintomas_coleta_dias_v17")
    if "data_puncao_lombar_v17" in d.columns:
        tem_pl = _dates(d, "data_puncao_lombar_v17").notna()
    else:
        tem_pl = lt.notna()
    valid = tem_pl & lt.notna() & (lt >= 0) & (lt < 365)
    den = int(valid.sum())
    s = lt[valid]
    n1 = int((s <= 1).sum())
    n2 = int((s <= 2).sum())
    return {
        "casos_total": int(len(d)),
        "casos_com_puncao": int(tem_pl.sum()),
        "coleta_com_lead_time": den,
        "coleta_le_1d_n": n1,
        "coleta_le_2d_n": n2,
        "pct_coleta_le_1d": _pct(n1, den),
        "pct_coleta_le_2d": _pct(n2, den),
        "p50_coleta_dias": _p(s, 0.5),
        "p90_coleta_dias": _p(s, 0.9),
    }


# ── 2. Tempo até quimioprofilaxia ────────────────────────────────────────────

def calc_tempo_quimioprofilaxia(d: pd.DataFrame) -> dict:
    """Mediana, P90 e % ≤2 dias do lead time notificação→quimioprofilaxia.

    Elegibilidade e execução reaproveitam o módulo 12 (DM/Hib + _quimio_realizada).
    """
    dd = ms._ensure_lead_times(d)
    elegivel = _clas(dd).isin(DM_HIB)
    realizada = ms._quimio_realizada(dd)
    lt = _num(dd, "lt_notificacao_quimioprofilaxia_dias_v17")
    valid = elegivel & lt.notna() & (lt >= 0) & (lt < 365)
    n_eleg = int(elegivel.sum())
    n_lt = int(valid.sum())
    s = lt[valid]
    n2 = int((s <= 2).sum())
    return {
        "elegiveis_dm_hib": n_eleg,
        "quimio_realizada_n": int((elegivel & realizada).sum()),
        "quimio_com_lead_time": n_lt,
        "quimio_le_2d_n": n2,
        "pct_quimio_le_2d_entre_elegiveis": _pct(n2, n_eleg),
        "pct_quimio_le_2d_entre_com_data": _pct(n2, n_lt),
        "pct_quimio_realizada": _pct(int((elegivel & realizada).sum()), n_eleg),
        "p50_quimio_dias": _p(s, 0.5),
        "p90_quimio_dias": _p(s, 0.9),
    }


# ── 3. Cobertura de sorogrupo em DM confirmada ───────────────────────────────

def calc_sorogrupo_dm(d: pd.DataFrame) -> dict:
    """% de DM confirmada com sorogrupo preenchido (pré-requisito NT 154/2024)."""
    clas = _clas(d)
    conf = _num(d, "confirmado_v17").fillna(0).astype(int)
    alvo = clas.eq(DM) & (conf == 1)
    den = int(alvo.sum())
    col = _soro_col(d)
    if col is None or den == 0:
        return {
            "dm_confirmada_n": den,
            "sorogrupo_preenchido_n": 0,
            "pct_sorogrupo_preenchido": np.nan,
            "dm_total_n": int(clas.eq(DM).sum()),
        }
    s = d.loc[alvo, col]
    ok = _filled(s) & ~s.astype(str).map(text_key).isin(SORO_VAZIO)
    num = int(ok.sum())
    return {
        "dm_confirmada_n": den,
        "sorogrupo_preenchido_n": num,
        "pct_sorogrupo_preenchido": _pct(num, den),
        "dm_total_n": int(clas.eq(DM).sum()),
    }


# ── 4. Contatos por caso de DM ───────────────────────────────────────────────

def calc_contatos_dm(d: pd.DataFrame) -> dict:
    """Mediana de comunicantes por caso de DM e % com zero ou sem informação."""
    dm = _clas(d).eq(DM)
    den = int(dm.sum())
    com = _num(d, "NumeroComunicantes")[dm]
    com_valid = com[(com >= 0) & com.notna()]
    sem_info = int(com.isna().sum())
    zeros = int((com_valid == 0).sum())
    return {
        "dm_n": den,
        "dm_com_info_comunicantes": int(com_valid.shape[0]),
        "dm_sem_info_comunicantes": sem_info,
        "dm_zero_comunicantes": zeros,
        "dm_zero_ou_sem_info_n": zeros + sem_info,
        "pct_dm_zero_ou_sem_info": _pct(zeros + sem_info, den),
        "p50_comunicantes_por_caso": _p(com_valid, 0.5),
        "p90_comunicantes_por_caso": _p(com_valid, 0.9),
        "total_comunicantes": float(com_valid.sum()) if len(com_valid) else np.nan,
    }


# ── 5. Subnotificação de mortalidade (SIM sem SINAN) ─────────────────────────

def _fonte_mortalidade_sim() -> tuple[bool, str]:
    for nome in ["desfechos_mortalidade_sim_v23.csv", "enriquecimento_casos_dw_v23.csv"]:
        if (OUT / nome).exists():
            return True, nome
    return False, ""


def calc_subnotificacao_mortalidade(d: pd.DataFrame) -> dict:
    """n e % de óbitos com CID de meningite no SIM sem desfecho de óbito no SINAN."""
    sim_sem_sinan = _num(d, "obito_sim_sem_sinan_v23").fillna(0).astype(int)
    sim_link = _num(d, "obito_sim_link_v23").fillna(0).astype(int)
    sinan = _num(d, "obito_meningite_v17").fillna(0).astype(int)
    uniao = _num(d, "obito_meningite_uniao_v23")
    if uniao.isna().all():
        uniao = ((sinan == 1) | (sim_link == 1)).astype(int)
    else:
        uniao = uniao.fillna(0).astype(int)
    n = int(sim_sem_sinan.sum())
    return {
        "casos_total": int(len(d)),
        "obitos_sinan_n": int(sinan.sum()),
        "obitos_sim_link_n": int(sim_link.sum()),
        "obitos_uniao_n": int(uniao.sum()),
        "obitos_sim_sem_sinan_n": n,
        "pct_sobre_obitos_sim": _pct(n, int(sim_link.sum())),
        "pct_sobre_obitos_uniao": _pct(n, int(uniao.sum())),
        "pct_sobre_casos": _pct(n, len(d)),
    }


# ── 6. Oportunidade de detecção ──────────────────────────────────────────────

def calc_oportunidade_deteccao(d: pd.DataFrame) -> dict:
    """Mediana e P90 do lead time sintomas→notificação."""
    lt = _num(d, "lt_sintomas_notificacao_dias_v17")
    valid = lt.notna() & (lt >= 0) & (lt < 365)
    s = lt[valid]
    den = int(valid.sum())
    n1 = int((s <= 1).sum())
    return {
        "casos_total": int(len(d)),
        "com_lead_time": den,
        "notificacao_le_1d_n": n1,
        "pct_notificacao_le_1d": _pct(n1, den),
        "p50_deteccao_dias": _p(s, 0.5),
        "p90_deteccao_dias": _p(s, 0.9),
    }


def build_oportunidade_deteccao(d: pd.DataFrame) -> pd.DataFrame:
    """Estadual + regional + ano + regional×classificação + classificação."""
    frames = [_por_escopo(d, calc_oportunidade_deteccao)]
    if "classificacao_agrupada_v17" in d.columns:
        rows = []
        for clas, g in d.groupby(_clas(d), dropna=False):
            row = {"escopo": "CLASSIFICACAO", "recorte": str(clas)}
            row.update(calc_oportunidade_deteccao(g))
            rows.append(row)
        if "regional_v17" in d.columns:
            reg = d["regional_v17"].fillna("Sem regional").astype(str)
            for (r, clas), g in d.groupby([reg, _clas(d)], dropna=False):
                row = {"escopo": "REGIONAL_CLASSIFICACAO", "recorte": f"{r} | {clas}"}
                row.update(calc_oportunidade_deteccao(g))
                rows.append(row)
        frames.append(pd.DataFrame(rows))
    return pd.concat([f for f in frames if not f.empty], ignore_index=True)


# ── 7. Casos sem denominador populacional ────────────────────────────────────

def calc_sem_denominador(d: pd.DataFrame) -> dict:
    """n e % de casos sem população de referência (incidência publicada é estimativa)."""
    flag = _num(d, "tem_denominador_populacional_v17")
    if flag.isna().all():
        pop = _num(d, "populacao_v17")
        flag = (pop.notna() & (pop > 0)).astype(int)
    else:
        flag = flag.fillna(0).astype(int)
    den = int(len(d))
    sem = int((flag == 0).sum())
    return {
        "casos_total": den,
        "com_denominador_n": int((flag == 1).sum()),
        "sem_denominador_n": sem,
        "pct_sem_denominador": _pct(sem, den),
    }


def build_denominador_por_ano(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transparência por ano: quais anos têm população IBGE real (match exato
    município×ano) vs sem denominador. Não há carry-forward no módulo 00 —
    fora da série disponível a incidência fica vazia.
    """
    if df.empty or "ano_evento_v17" not in df.columns:
        return pd.DataFrame()
    d = df.copy()
    flag = _num(d, "tem_denominador_populacional_v17")
    if flag.isna().all():
        pop = _num(d, "populacao_v17")
        flag = (pop.notna() & (pop > 0)).astype(int)
    else:
        flag = flag.fillna(0).astype(int)
    d["_tem_denom"] = flag
    rows = []
    for ano, g in d.groupby(pd.to_numeric(d["ano_evento_v17"], errors="coerce"), dropna=False):
        if pd.isna(ano):
            continue
        total = int(len(g))
        com = int(g["_tem_denom"].sum())
        sem = total - com
        if com == total and total > 0:
            status = "denominador_real_ibge"
        elif com == 0:
            status = "sem_denominador"
        else:
            status = "parcial"
        rows.append({
            "ano_evento_v17": int(ano),
            "casos_total": total,
            "com_denominador_n": com,
            "sem_denominador_n": sem,
            "pct_sem_denominador": _pct(sem, total),
            "status_denominador": status,
            "politica": "match_exato_municipio_ano_sem_carry_forward",
            "serie_populacional_disponivel": "2010-2025 (populacao_padronizada_mt.csv; RIPSA/MS + arquivo local)",
            "nota": (
                "Série 2010–2025 via populacao_padronizada_mt.csv "
                "(RIPSA/MS 2010–2019 + arquivo local 2020–2025). "
                "Anos <2010 e 2026+ ficam sem denominador (sem carry-forward). "
                "Atualize com 31_atualizar_populacao_ibge_ripsa_v31.py quando houver estimativa nova."
            ),
        })
    return pd.DataFrame(rows).sort_values("ano_evento_v17")


# ── 8. Completude dos campos essenciais ──────────────────────────────────────

def calc_completude(d: pd.DataFrame) -> dict:
    """Completude média dos campos essenciais do módulo 11 e pior campo."""
    presentes = [c for c in CAMPOS_ESSENCIAIS if c in d.columns]
    out: dict = {"casos_total": int(len(d)), "campos_avaliados": len(presentes)}
    if not presentes or d.empty:
        out.update({"pct_completude_media": np.nan, "campo_pior": "", "pct_campo_pior": np.nan})
        return out
    pcts = {}
    for c in presentes:
        pcts[c] = float(_filled(d[c]).mean() * 100)
        out[f"comp_{c}"] = pcts[c]
    pior = min(pcts, key=lambda k: pcts[k])
    out["pct_completude_media"] = float(np.nanmean(list(pcts.values())))
    out["campo_pior"] = pior
    out["pct_campo_pior"] = pcts[pior]
    return out


def build_completude(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    reg = _por_escopo(d, calc_completude, incluir_ano=False)
    if not reg.empty and "pct_completude_media" in reg.columns:
        reg = reg.sort_values(
            ["escopo", "pct_completude_media"], ascending=[True, True]
        ).reset_index(drop=True)
        reg["ranking_completude"] = (
            reg[reg["escopo"].eq("REGIONAL")]["pct_completude_media"].rank(ascending=False, method="min")
        )

    keys = [c for c in ["codigo_municipio_v17", "municipio_v17", "regional_v17"] if c in d.columns]
    rows = []
    if keys:
        for vals, g in d.groupby(keys, dropna=False):
            if not isinstance(vals, tuple):
                vals = (vals,)
            row = {k: v for k, v in zip(keys, vals)}
            row.update(calc_completude(g))
            rows.append(row)
    mun = pd.DataFrame(rows)
    if not mun.empty and "pct_completude_media" in mun.columns:
        mun = mun.sort_values("pct_completude_media", ascending=True).reset_index(drop=True)
        mun["ranking_completude"] = mun["pct_completude_media"].rank(ascending=False, method="min")
    return reg, mun


# ── 9. Letalidade padronizada por idade ──────────────────────────────────────

def _prepara_faixa(d: pd.DataFrame) -> pd.DataFrame:
    """Reaproveita a regra de faixa etária do Informe (módulo 14)."""
    out = d.copy()
    if "faixa_informe_v23" in out.columns:
        return out
    base = out["FaixaEtaria"] if "FaixaEtaria" in out.columns else pd.Series(index=out.index, dtype=object)
    out["faixa_informe_v23"] = base.map(epi.map_faixa_informe)
    if "IdadePaciente" in out.columns:
        idade = pd.to_numeric(
            out["IdadePaciente"].astype(str).str.extract(r"(\d+[.,]?\d*)", expand=False).str.replace(",", "."),
            errors="coerce",
        )
        miss = out["faixa_informe_v23"].eq("Ignorado/sem informação") & idade.notna()
        out.loc[miss, "faixa_informe_v23"] = idade.loc[miss].map(epi.map_faixa_informe)
    return out


def _desfechos_letalidade(d: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Denominador (confirmados, com fallback para casos) e óbitos por meningite."""
    conf = _num(d, "confirmado_v17").fillna(0).astype(int)
    obito = _num(d, "obito_meningite_uniao_v23")
    if obito.isna().all():
        obito = _num(d, "obito_meningite_v17")
    obito = obito.fillna(0).astype(int)
    return conf, obito


def calc_letalidade_padronizada(d: pd.DataFrame, pesos: pd.Series) -> dict:
    """Letalidade bruta e padronizada por faixa etária (padronização direta).

    `pesos` é a distribuição etária dos casos do estado no período. Faixas sem
    casos na unidade não têm taxa estimável: os pesos são renormalizados entre
    as faixas cobertas e `peso_coberto_pct` informa quanto da população-padrão
    foi efetivamente usada.
    """
    dd = _prepara_faixa(d)
    conf, obito = _desfechos_letalidade(dd)
    base = conf.eq(1)
    if not base.any():
        base = pd.Series(True, index=dd.index)
    den = int(base.sum())
    num = int(obito[base].sum())
    bruta = _pct(num, den)

    faixa = dd.loc[base, "faixa_informe_v23"].astype(str)
    ob = obito[base]
    taxas, w = {}, {}
    for f, idx in faixa.groupby(faixa).groups.items():
        n_f = len(idx)
        if n_f == 0 or f not in pesos.index:
            continue
        taxas[f] = float(ob.loc[idx].sum()) / n_f * 100
        w[f] = float(pesos.get(f, 0.0))
    peso_total = float(sum(w.values()))
    if peso_total > 0:
        padron = sum(taxas[f] * w[f] for f in taxas) / peso_total
    else:
        padron = np.nan
    return {
        "casos_n": int(len(dd)),
        "denominador_letalidade_n": den,
        "obitos_n": num,
        "letalidade_bruta_pct": bruta,
        "letalidade_padronizada_pct": padron,
        "peso_coberto_pct": peso_total * 100 if peso_total else 0.0,
        "faixas_com_casos": len(taxas),
    }


def build_letalidade_padronizada(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    dd = _prepara_faixa(d)
    conf, _ = _desfechos_letalidade(dd)
    base = dd[conf.eq(1)] if conf.eq(1).any() else dd
    pesos = base["faixa_informe_v23"].astype(str).value_counts(normalize=True)

    linhas_reg = []
    for escopo, recorte, g in _iter_escopos(dd, incluir_ano=False):
        row = {"escopo": escopo, "recorte": recorte}
        row.update(calc_letalidade_padronizada(g, pesos))
        linhas_reg.append(row)
    reg = pd.DataFrame(linhas_reg)

    keys = [c for c in ["codigo_municipio_v17", "municipio_v17", "regional_v17"] if c in dd.columns]
    rows = []
    if keys:
        for vals, g in dd.groupby(keys, dropna=False):
            if not isinstance(vals, tuple):
                vals = (vals,)
            row = {"escopo": "MUNICIPIO"}
            row.update({k: v for k, v in zip(keys, vals)})
            row.update(calc_letalidade_padronizada(g, pesos))
            rows.append(row)
    mun = pd.DataFrame(rows)
    if not mun.empty:
        mun = mun.sort_values(
            ["letalidade_padronizada_pct", "denominador_letalidade_n"], ascending=[False, False]
        ).reset_index(drop=True)

    pesos_df = pesos.rename_axis("faixa_informe_v23").reset_index(name="peso_padrao")
    pesos_df["ordem"] = pesos_df["faixa_informe_v23"].map(
        {f: i for i, f in enumerate(FAIXA_ORDER)}
    ).fillna(99)
    pesos_df = pesos_df.sort_values("ordem").drop(columns=["ordem"])
    return pd.concat([reg, mun], ignore_index=True), pesos_df


# ── Opcional: varredura espaço-temporal de DM ────────────────────────────────

def build_aglomerado_espaco_temporal(d: pd.DataFrame, janela: int = 4, baseline: int = 52,
                                     ultimas_semanas: int = 26) -> pd.DataFrame:
    """Município × semana: razão observado/esperado em janela móvel para DM.

    Esperado = média semanal do próprio município nas `baseline` semanas
    anteriores à janela, multiplicada pelo tamanho da janela. Sinaliza
    aglomerado emergente quando obs ≥ 2 e O/E ≥ 2.
    """
    dm = d[_clas(d).eq(DM)].copy()
    if dm.empty or "municipio_v17" not in dm.columns:
        return pd.DataFrame()
    ref = _dates(dm, "data_ref_v17")
    dm = dm[ref.notna()].copy()
    if dm.empty:
        return pd.DataFrame()
    ref = ref[ref.notna()]
    # índice semanal contínuo (segunda-feira da semana ISO)
    dm["_semana"] = ref.dt.to_period("W-SUN").dt.start_time
    counts = dm.groupby(["_semana", "municipio_v17"]).size().rename("casos").reset_index()
    wide = counts.pivot_table(index="_semana", columns="municipio_v17", values="casos", aggfunc="sum")
    idx = pd.date_range(wide.index.min(), wide.index.max(), freq="7D")
    wide = wide.reindex(idx).fillna(0.0)
    if len(wide) < janela + 2:
        return pd.DataFrame()

    obs = wide.rolling(janela, min_periods=1).sum()
    esp = wide.shift(janela).rolling(baseline, min_periods=janela).mean() * janela
    corte = wide.index.max() - pd.Timedelta(weeks=ultimas_semanas)

    o = obs[obs.index >= corte].stack().rename("observado").reset_index()
    e = esp[esp.index >= corte].stack().rename("esperado").reset_index()
    o.columns = ["semana_inicio", "municipio_v17", "observado"]
    e.columns = ["semana_inicio", "municipio_v17", "esperado"]
    out = o.merge(e, on=["semana_inicio", "municipio_v17"], how="left")
    out = out[out["observado"] > 0].copy()
    if out.empty:
        return pd.DataFrame()
    esp_min = 0.25
    out["esperado_ajustado"] = out["esperado"].fillna(0).clip(lower=esp_min)
    out["razao_obs_esp"] = out["observado"] / out["esperado_ajustado"]
    out["aglomerado_emergente"] = ((out["observado"] >= 2) & (out["razao_obs_esp"] >= 2)).astype(int)
    out["janela_semanas"] = janela
    if "regional_v17" in d.columns:
        mapa = (
            d.dropna(subset=["municipio_v17"])
            .drop_duplicates("municipio_v17")
            .set_index("municipio_v17")["regional_v17"]
            .to_dict()
        )
        out["regional_v17"] = out["municipio_v17"].map(mapa)
    return out.sort_values(
        ["aglomerado_emergente", "razao_obs_esp", "semana_inicio"], ascending=[False, False, False]
    ).reset_index(drop=True)


# ── Relatório ────────────────────────────────────────────────────────────────

def _val(resumo: pd.DataFrame, indicador: str, escopo: str = "ESTADUAL"):
    sub = resumo[(resumo["indicador"] == indicador) & (resumo["escopo"] == escopo)]
    if sub.empty:
        return np.nan, np.nan, np.nan
    r = sub.iloc[0]
    return r.get("valor"), r.get("numerador"), r.get("denominador")


def write_report(resumo: pd.DataFrame, comp_reg: pd.DataFrame, letal: pd.DataFrame,
                 mort_ok: bool, mort_fonte: str, aglo: pd.DataFrame) -> str:
    def linha(rotulo, indicador, unidade="%"):
        v, n, dd = _val(resumo, indicador)
        suf = "%" if unidade == "%" else f" {unidade}"
        det = ""
        if pd.notna(n) and pd.notna(dd):
            det = f" (n={fmt_num(n, 0)}/{fmt_num(dd, 0)})"
        return f"- {rotulo}: **{fmt_num(v)}{suf}**{det}"

    lines = [
        "# Indicadores novos V28 — Meningites CIEVS-MT",
        "",
        f"**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "> Números estaduais. Recortes por regional e por ano estão nos CSVs `*_v28.csv`.",
        "",
        "## Oportunidade de coleta liquórica",
        "",
        linha("Coleta ≤1 dia dos sintomas", "pct_coleta_le_1d"),
        linha("Coleta ≤2 dias dos sintomas", "pct_coleta_le_2d"),
        linha("Mediana sintomas→coleta", "p50_coleta_dias", "dia(s)"),
        linha("P90 sintomas→coleta", "p90_coleta_dias", "dia(s)"),
        "",
        "## Tempo até quimioprofilaxia (DM e Hib)",
        "",
        linha("Quimio ≤2 dias entre elegíveis", "pct_quimio_le_2d_entre_elegiveis"),
        linha("Quimio ≤2 dias entre casos com data", "pct_quimio_le_2d_entre_com_data"),
        linha("Mediana notificação→quimio", "p50_quimio_dias", "dia(s)"),
        linha("P90 notificação→quimio", "p90_quimio_dias", "dia(s)"),
        "",
        "## Cobertura de sorogrupo em DM confirmada (NT 154/2024)",
        "",
        linha("DM confirmada com sorogrupo preenchido", "pct_sorogrupo_preenchido"),
        "",
        "## Contatos por caso de DM",
        "",
        linha("Mediana de comunicantes por caso de DM", "p50_comunicantes_por_caso", "contatos"),
        linha("DM com zero ou sem informação de comunicantes", "pct_dm_zero_ou_sem_info"),
        "",
        "## Subnotificação de mortalidade (SIM sem SINAN)",
        "",
    ]
    if mort_ok:
        lines += [
            f"Fonte do linkage: `{mort_fonte}`.",
            "",
            linha("Óbitos SIM sem desfecho no SINAN (sobre óbitos SIM)", "pct_sobre_obitos_sim"),
            linha("Óbitos SIM sem desfecho no SINAN (sobre óbitos SINAN∪SIM)", "pct_sobre_obitos_uniao"),
        ]
    else:
        lines.append(
            "**Indisponível** — `desfechos_mortalidade_sim_v23.csv` / `enriquecimento_casos_dw_v23.csv` "
            "ausentes. Rode os módulos 19/20 (extração e enriquecimento DW)."
        )
    lines += [
        "",
        "## Oportunidade de detecção (sintomas→notificação)",
        "",
        linha("Mediana", "p50_deteccao_dias", "dia(s)"),
        linha("P90", "p90_deteccao_dias", "dia(s)"),
        linha("Notificação ≤1 dia dos sintomas", "pct_notificacao_le_1d"),
        "",
        "## Casos sem denominador populacional",
        "",
        linha("Casos sem população de referência", "pct_sem_denominador"),
        "",
        "## Completude dos campos essenciais",
        "",
        linha("Completude média dos campos essenciais", "pct_completude_media"),
    ]
    if not comp_reg.empty:
        piores = comp_reg[comp_reg["escopo"].eq("REGIONAL")].nsmallest(5, "pct_completude_media")
        for _, r in piores.iterrows():
            lines.append(
                f"  - {r['recorte']}: {fmt_num(r['pct_completude_media'])}% "
                f"(pior campo: {r.get('campo_pior')} = {fmt_num(r.get('pct_campo_pior'))}%)"
            )
    lines += ["", "## Letalidade padronizada por idade", ""]
    if not letal.empty:
        est = letal[letal["escopo"].eq("ESTADUAL")]
        if not est.empty:
            r = est.iloc[0]
            lines += [
                f"- Estadual: bruta **{fmt_num(r['letalidade_bruta_pct'])}%** · "
                f"padronizada **{fmt_num(r['letalidade_padronizada_pct'])}%** "
                f"(óbitos {fmt_num(r['obitos_n'], 0)}/{fmt_num(r['denominador_letalidade_n'], 0)})",
            ]
        mun = letal[letal["escopo"].eq("MUNICIPIO")]
        mun = mun[pd.to_numeric(mun["denominador_letalidade_n"], errors="coerce") >= 10]
        if not mun.empty:
            lines.append("- Municípios com n≥10 e maior letalidade padronizada:")
            for _, r in mun.head(5).iterrows():
                lines.append(
                    f"  - {r.get('municipio_v17')}: padronizada {fmt_num(r['letalidade_padronizada_pct'])}% "
                    f"· bruta {fmt_num(r['letalidade_bruta_pct'])}% · n={fmt_num(r['denominador_letalidade_n'], 0)}"
                )
    lines += [
        "",
        "> Padronização direta por faixa etária do Informe; população-padrão = distribuição "
        "etária dos casos do estado no período. Faixas sem casos no município não entram na "
        "taxa: confira `peso_coberto_pct` antes de comparar municípios pequenos.",
        "",
    ]
    if aglo is not None and not aglo.empty:
        emerg = aglo[aglo["aglomerado_emergente"].eq(1)]
        lines += [
            "## Varredura espaço-temporal (DM, exploratória)",
            "",
            f"- Janelas com sinal: **{fmt_num(len(emerg), 0)}** em "
            f"**{fmt_num(emerg['municipio_v17'].nunique(), 0)}** município(s)",
        ]
        # janelas móveis se sobrepõem: mostra a mais recente por município
        emerg = emerg.sort_values("semana_inicio", ascending=False).drop_duplicates("municipio_v17")
        for _, r in emerg.head(5).iterrows():
            lines.append(
                f"  - {r['municipio_v17']} · semana de {pd.to_datetime(r['semana_inicio']).date()}: "
                f"obs {fmt_num(r['observado'], 0)} vs esperado {fmt_num(r['esperado_ajustado'])} "
                f"(O/E {fmt_num(r['razao_obs_esp'])})"
            )
        lines += ["", "> Sinal exploratório; exige validação no território antes de qualquer ação.", ""]
    lines += [
        "## Como atualizar",
        "",
        "```bat",
        "py -3.13 28_indicadores_novos_v28.py",
        "```",
        "",
    ]
    text = "\n".join(lines)
    (REL / "INDICADORES_NOVOS_V28.md").write_text(text, encoding="utf-8")
    return text


# ── Orquestração do módulo ───────────────────────────────────────────────────

def main() -> int:
    df = load_base_v17()
    if df is None or df.empty:
        print("[ERRO] Base V17 ausente. Rode 00_base_unica_meningites_v17.py.")
        return 1
    print(f"[INFO] Base carregada: {len(df):,} registros · {df.shape[1]} colunas".replace(",", "."))

    longo: list[dict] = []

    # 1) Oportunidade de coleta liquórica
    coleta = _por_escopo(df, calc_coleta_liquorica)
    coleta.to_csv(OUT / "oportunidade_coleta_liquor_v28.csv", index=False, encoding="utf-8-sig")
    longo += _to_long(coleta, {
        "pct_coleta_le_1d": ("pct_coleta_le_1d", "%", "coleta_le_1d_n", "coleta_com_lead_time"),
        "pct_coleta_le_2d": ("pct_coleta_le_2d", "%", "coleta_le_2d_n", "coleta_com_lead_time"),
        "p50_coleta_dias": ("p50_coleta_dias", "dias", None, "coleta_com_lead_time"),
        "p90_coleta_dias": ("p90_coleta_dias", "dias", None, "coleta_com_lead_time"),
    }, "oportunidade_coleta_liquor")
    print(f"[OK] Coleta liquórica: {len(coleta)} linhas de escopo.")

    # 2) Tempo até quimioprofilaxia
    quimio = _por_escopo(df, calc_tempo_quimioprofilaxia)
    quimio.to_csv(OUT / "tempo_quimioprofilaxia_v28.csv", index=False, encoding="utf-8-sig")
    longo += _to_long(quimio, {
        "pct_quimio_le_2d_entre_elegiveis": ("pct_quimio_le_2d_entre_elegiveis", "%", "quimio_le_2d_n", "elegiveis_dm_hib"),
        "pct_quimio_le_2d_entre_com_data": ("pct_quimio_le_2d_entre_com_data", "%", "quimio_le_2d_n", "quimio_com_lead_time"),
        "pct_quimio_realizada": ("pct_quimio_realizada", "%", "quimio_realizada_n", "elegiveis_dm_hib"),
        "p50_quimio_dias": ("p50_quimio_dias", "dias", None, "quimio_com_lead_time"),
        "p90_quimio_dias": ("p90_quimio_dias", "dias", None, "quimio_com_lead_time"),
    }, "tempo_quimioprofilaxia")
    print(f"[OK] Tempo até quimioprofilaxia: {len(quimio)} linhas de escopo.")

    # 3) Cobertura de sorogrupo em DM confirmada
    soro = _por_escopo(df, calc_sorogrupo_dm)
    soro.to_csv(OUT / "cobertura_sorogrupo_dm_v28.csv", index=False, encoding="utf-8-sig")
    longo += _to_long(soro, {
        "pct_sorogrupo_preenchido": ("pct_sorogrupo_preenchido", "%", "sorogrupo_preenchido_n", "dm_confirmada_n"),
    }, "cobertura_sorogrupo_dm")
    print(f"[OK] Cobertura de sorogrupo em DM confirmada: {len(soro)} linhas de escopo.")

    # 4) Contatos por caso de DM
    contatos = _por_escopo(df, calc_contatos_dm)
    contatos.to_csv(OUT / "contatos_por_caso_dm_v28.csv", index=False, encoding="utf-8-sig")
    longo += _to_long(contatos, {
        "p50_comunicantes_por_caso": ("p50_comunicantes_por_caso", "contatos", None, "dm_com_info_comunicantes"),
        "p90_comunicantes_por_caso": ("p90_comunicantes_por_caso", "contatos", None, "dm_com_info_comunicantes"),
        "pct_dm_zero_ou_sem_info": ("pct_dm_zero_ou_sem_info", "%", "dm_zero_ou_sem_info_n", "dm_n"),
    }, "contatos_por_caso_dm")
    print(f"[OK] Contatos por caso de DM: {len(contatos)} linhas de escopo.")

    # 5) Subnotificação de mortalidade
    mort_ok, mort_fonte = _fonte_mortalidade_sim()
    if mort_ok:
        mort = _por_escopo(df, calc_subnotificacao_mortalidade)
        mort["fonte_linkage"] = mort_fonte
        mort["disponivel"] = 1
        longo += _to_long(mort, {
            "pct_sobre_obitos_sim": ("pct_sobre_obitos_sim", "%", "obitos_sim_sem_sinan_n", "obitos_sim_link_n"),
            "pct_sobre_obitos_uniao": ("pct_sobre_obitos_uniao", "%", "obitos_sim_sem_sinan_n", "obitos_uniao_n"),
            "pct_sobre_casos": ("pct_sobre_casos", "%", "obitos_sim_sem_sinan_n", "casos_total"),
        }, "subnotificacao_mortalidade")
        print(f"[OK] Subnotificação de mortalidade (fonte {mort_fonte}).")
    else:
        mort = pd.DataFrame([{
            "escopo": "ESTADUAL",
            "recorte": ESCOPO_ESTADUAL,
            "casos_total": int(len(df)),
            "obitos_sim_sem_sinan_n": np.nan,
            "pct_sobre_obitos_sim": np.nan,
            "pct_sobre_obitos_uniao": np.nan,
            "pct_sobre_casos": np.nan,
            "fonte_linkage": "",
            "disponivel": 0,
        }])
        longo.append({
            "familia": "subnotificacao_mortalidade",
            "indicador": "pct_sobre_obitos_sim",
            "escopo": "ESTADUAL",
            "recorte": ESCOPO_ESTADUAL,
            "valor": np.nan,
            "numerador": np.nan,
            "denominador": np.nan,
            "unidade": "%",
        })
        print("[AVISO] Linkage SIM ausente — subnotificação de mortalidade registrada como indisponível.")
    mort.to_csv(OUT / "subnotificacao_mortalidade_v28.csv", index=False, encoding="utf-8-sig")

    # 6) Oportunidade de detecção
    deteccao = build_oportunidade_deteccao(df)
    deteccao.to_csv(OUT / "oportunidade_deteccao_v28.csv", index=False, encoding="utf-8-sig")
    longo += _to_long(deteccao, {
        "p50_deteccao_dias": ("p50_deteccao_dias", "dias", None, "com_lead_time"),
        "p90_deteccao_dias": ("p90_deteccao_dias", "dias", None, "com_lead_time"),
        "pct_notificacao_le_1d": ("pct_notificacao_le_1d", "%", "notificacao_le_1d_n", "com_lead_time"),
    }, "oportunidade_deteccao")
    print(f"[OK] Oportunidade de detecção: {len(deteccao)} linhas de escopo.")

    # 7) Casos sem denominador populacional
    denom = _por_escopo(df, calc_sem_denominador)
    denom.to_csv(OUT / "casos_sem_denominador_populacional_v28.csv", index=False, encoding="utf-8-sig")
    longo += _to_long(denom, {
        "pct_sem_denominador": ("pct_sem_denominador", "%", "sem_denominador_n", "casos_total"),
    }, "casos_sem_denominador_populacional")
    denom_ano = build_denominador_por_ano(df)
    if not denom_ano.empty:
        denom_ano.to_csv(OUT / "denominador_populacional_por_ano_v28.csv", index=False, encoding="utf-8-sig")
        print(
            f"[OK] Denominador por ano: "
            f"{int((denom_ano['status_denominador'] == 'denominador_real_ibge').sum())} anos com IBGE real · "
            f"{int((denom_ano['status_denominador'] == 'sem_denominador').sum())} sem denominador "
            f"(sem carry-forward)."
        )
    print(f"[OK] Casos sem denominador populacional: {len(denom)} linhas de escopo.")

    # 8) Completude dos campos essenciais
    comp_reg, comp_mun = build_completude(df)
    comp_reg.to_csv(OUT / "completude_essenciais_regional_v28.csv", index=False, encoding="utf-8-sig")
    comp_mun.to_csv(OUT / "completude_essenciais_municipio_v28.csv", index=False, encoding="utf-8-sig")
    longo += _to_long(comp_reg, {
        "pct_completude_media": ("pct_completude_media", "%", None, "casos_total"),
        "pct_campo_pior": ("pct_campo_pior", "%", None, "casos_total"),
    }, "completude_essenciais")
    print(f"[OK] Completude dos campos essenciais: {len(comp_reg)} escopos · {len(comp_mun)} municípios.")

    # 9) Letalidade padronizada por idade
    letal, pesos = build_letalidade_padronizada(df)
    letal.to_csv(OUT / "letalidade_padronizada_idade_v28.csv", index=False, encoding="utf-8-sig")
    pesos.to_csv(OUT / "letalidade_populacao_padrao_v28.csv", index=False, encoding="utf-8-sig")
    longo += _to_long(letal[letal["escopo"].isin(["ESTADUAL", "REGIONAL"])], {
        "letalidade_bruta_pct": ("letalidade_bruta_pct", "%", "obitos_n", "denominador_letalidade_n"),
        "letalidade_padronizada_pct": ("letalidade_padronizada_pct", "%", "obitos_n", "denominador_letalidade_n"),
    }, "letalidade_padronizada_idade")
    print(f"[OK] Letalidade padronizada: {len(letal)} linhas (estadual/regional/município).")

    # Opcional — varredura espaço-temporal DM
    aglo = pd.DataFrame()
    try:
        aglo = build_aglomerado_espaco_temporal(df)
        if not aglo.empty:
            aglo.to_csv(OUT / "aglomerado_espaco_temporal_v28.csv", index=False, encoding="utf-8-sig")
            print(f"[OK] Varredura espaço-temporal DM: {int(aglo['aglomerado_emergente'].sum())} sinal(is).")
    except Exception as e:
        print(f"[AVISO] Varredura espaço-temporal não gerada: {e}")

    # Resumo longo para o painel
    resumo = pd.DataFrame(longo)
    if not resumo.empty:
        resumo = resumo[["familia", "indicador", "escopo", "recorte", "valor", "numerador", "denominador", "unidade"]]
        resumo["gerado_em"] = datetime.now().isoformat(timespec="seconds")
    resumo.to_csv(OUT / "indicadores_novos_resumo_v28.csv", index=False, encoding="utf-8-sig")
    print(f"[OK] Resumo longo: {len(resumo)} linhas -> indicadores_novos_resumo_v28.csv")

    write_report(resumo, comp_reg, letal, mort_ok, mort_fonte, aglo)
    print(f"[OK] Relatório -> {REL / 'INDICADORES_NOVOS_V28.md'}")

    est = resumo[resumo["escopo"].eq("ESTADUAL")] if not resumo.empty else pd.DataFrame()
    if not est.empty:
        print("\n--- Estadual ---")
        print(est[["indicador", "valor", "numerador", "denominador", "unidade"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
