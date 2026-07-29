# -*- coding: utf-8 -*-
"""Contratos e cálculos dos indicadores novos V28 (módulo 28_indicadores_novos_v28.py)."""
from __future__ import annotations

import importlib
import math
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "saida_meningites_v17"
DEMO = ROOT / "demo_cloud" / "saida_meningites_v17"

# Artefatos do módulo 28 e colunas mínimas de cada um
CONTRATOS_V28 = {
    "oportunidade_coleta_liquor_v28.csv": [
        "escopo", "recorte", "casos_com_puncao", "coleta_com_lead_time",
        "pct_coleta_le_1d", "pct_coleta_le_2d", "p50_coleta_dias", "p90_coleta_dias",
    ],
    "tempo_quimioprofilaxia_v28.csv": [
        "escopo", "recorte", "elegiveis_dm_hib", "quimio_le_2d_n",
        "pct_quimio_le_2d_entre_elegiveis", "p50_quimio_dias", "p90_quimio_dias",
    ],
    "cobertura_sorogrupo_dm_v28.csv": [
        "escopo", "recorte", "dm_confirmada_n", "sorogrupo_preenchido_n", "pct_sorogrupo_preenchido",
    ],
    "contatos_por_caso_dm_v28.csv": [
        "escopo", "recorte", "dm_n", "p50_comunicantes_por_caso", "pct_dm_zero_ou_sem_info",
    ],
    "subnotificacao_mortalidade_v28.csv": [
        "escopo", "recorte", "obitos_sim_sem_sinan_n", "pct_sobre_obitos_sim", "disponivel",
    ],
    "oportunidade_deteccao_v28.csv": [
        "escopo", "recorte", "com_lead_time", "p50_deteccao_dias", "p90_deteccao_dias",
    ],
    "casos_sem_denominador_populacional_v28.csv": [
        "escopo", "recorte", "casos_total", "sem_denominador_n", "pct_sem_denominador",
    ],
    "completude_essenciais_regional_v28.csv": [
        "escopo", "recorte", "casos_total", "pct_completude_media", "campo_pior",
    ],
    "completude_essenciais_municipio_v28.csv": [
        "municipio_v17", "casos_total", "pct_completude_media",
    ],
    "letalidade_padronizada_idade_v28.csv": [
        "escopo", "casos_n", "denominador_letalidade_n", "obitos_n",
        "letalidade_bruta_pct", "letalidade_padronizada_pct", "peso_coberto_pct",
    ],
    "indicadores_novos_resumo_v28.csv": [
        "indicador", "escopo", "recorte", "valor", "numerador", "denominador", "unidade",
    ],
}


def _pick(nome: str) -> Path | None:
    for p in (OUT / nome, DEMO / nome):
        if p.exists():
            return p
    return None


def _mod28():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    return importlib.import_module("28_indicadores_novos_v28")


class TestContratosV28(unittest.TestCase):
    """Presença e schema dos artefatos gerados pelo módulo 28."""

    def test_artefatos_e_colunas(self):
        faltando = []
        for nome, cols in CONTRATOS_V28.items():
            p = _pick(nome)
            if p is None:
                faltando.append(nome)
                continue
            df = pd.read_csv(p)
            for col in cols:
                self.assertIn(col, df.columns, f"{nome}: coluna {col} ausente")
            self.assertGreater(len(df), 0, f"{nome} está vazio")
        if faltando and len(faltando) == len(CONTRATOS_V28):
            self.skipTest("módulo 28 ainda não gerado (py -3.13 28_indicadores_novos_v28.py)")
        self.assertEqual(faltando, [], f"artefatos V28 ausentes: {faltando}")

    def test_resumo_longo_tem_escopos(self):
        p = _pick("indicadores_novos_resumo_v28.csv")
        if p is None:
            self.skipTest("resumo V28 ainda não gerado")
        df = pd.read_csv(p)
        escopos = set(df["escopo"].astype(str))
        self.assertIn("ESTADUAL", escopos)
        self.assertIn("REGIONAL", escopos)
        # famílias esperadas de indicador
        inds = set(df["indicador"].astype(str))
        for esperado in [
            "pct_coleta_le_2d", "pct_quimio_le_2d_entre_elegiveis", "pct_sorogrupo_preenchido",
            "p50_comunicantes_por_caso", "p50_deteccao_dias", "pct_sem_denominador",
            "pct_completude_media", "letalidade_padronizada_pct",
        ]:
            self.assertIn(esperado, inds, f"indicador {esperado} ausente do resumo longo")


class TestSanidadeValoresV28(unittest.TestCase):
    """Percentuais entre 0 e 100, denominador ≥ numerador, medianas não negativas."""

    @classmethod
    def setUpClass(cls):
        p = _pick("indicadores_novos_resumo_v28.csv")
        cls.resumo = pd.read_csv(p) if p is not None else None

    def setUp(self):
        if self.resumo is None:
            self.skipTest("resumo V28 ainda não gerado")

    def test_percentuais_entre_0_e_100(self):
        pct = self.resumo[self.resumo["unidade"].astype(str).eq("%")]
        v = pd.to_numeric(pct["valor"], errors="coerce").dropna()
        self.assertFalse(v.empty, "nenhum percentual no resumo")
        self.assertGreaterEqual(float(v.min()), 0.0)
        self.assertLessEqual(float(v.max()), 100.0)

    def test_denominador_maior_ou_igual_numerador(self):
        num = pd.to_numeric(self.resumo["numerador"], errors="coerce")
        den = pd.to_numeric(self.resumo["denominador"], errors="coerce")
        ok = num.notna() & den.notna()
        self.assertTrue(ok.any(), "nenhum par numerador/denominador no resumo")
        ruins = self.resumo[ok & (num > den)]
        self.assertTrue(ruins.empty, f"numerador > denominador em:\n{ruins.head()}")

    def test_medianas_e_p90_nao_negativos(self):
        tempo = self.resumo[self.resumo["unidade"].astype(str).isin(["dias", "contatos"])]
        v = pd.to_numeric(tempo["valor"], errors="coerce").dropna()
        self.assertFalse(v.empty, "nenhuma mediana/P90 no resumo")
        self.assertGreaterEqual(float(v.min()), 0.0)

    def test_p90_nao_menor_que_p50(self):
        chaves = [("p50_coleta_dias", "p90_coleta_dias"),
                  ("p50_quimio_dias", "p90_quimio_dias"),
                  ("p50_deteccao_dias", "p90_deteccao_dias")]
        for p50, p90 in chaves:
            a = self.resumo[self.resumo["indicador"].eq(p50)].set_index(["escopo", "recorte"])["valor"]
            b = self.resumo[self.resumo["indicador"].eq(p90)].set_index(["escopo", "recorte"])["valor"]
            comum = a.index.intersection(b.index)
            if comum.empty:
                continue
            diff = pd.to_numeric(b.loc[comum], errors="coerce") - pd.to_numeric(a.loc[comum], errors="coerce")
            self.assertGreaterEqual(float(diff.dropna().min()), 0.0, f"{p90} < {p50}")

    def test_peso_padronizacao_ate_100(self):
        p = _pick("letalidade_padronizada_idade_v28.csv")
        if p is None:
            self.skipTest("letalidade padronizada ainda não gerada")
        df = pd.read_csv(p)
        peso = pd.to_numeric(df["peso_coberto_pct"], errors="coerce").dropna()
        self.assertGreaterEqual(float(peso.min()), 0.0)
        self.assertLessEqual(float(peso.max()), 100.0 + 1e-6)
        for col in ["letalidade_bruta_pct", "letalidade_padronizada_pct"]:
            v = pd.to_numeric(df[col], errors="coerce").dropna()
            self.assertGreaterEqual(float(v.min()), 0.0)
            self.assertLessEqual(float(v.max()), 100.0)


class TestCalculosV28(unittest.TestCase):
    """Cálculo de verdade: DataFrame sintético → valor esperado à mão."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.m = _mod28()
        except Exception as e:  # pandas/numpy ausentes ou base indisponível
            cls.m = None
            cls.erro = e

    def setUp(self):
        if self.m is None:
            self.skipTest(f"módulo 28 não importável: {getattr(self, 'erro', '')}")

    def test_pct_protege_denominador_zero(self):
        self.assertTrue(math.isnan(self.m._pct(3, 0)))
        self.assertTrue(math.isnan(self.m._pct(3, None)))
        self.assertAlmostEqual(self.m._pct(1, 4), 25.0)

    def test_coleta_liquorica(self):
        df = pd.DataFrame({
            "data_puncao_lombar_v17": ["2024-01-02", "2024-01-03", "2024-01-05", "2024-01-10", None],
            "lt_sintomas_coleta_dias_v17": [1, 2, 4, 9, 3],
        })
        r = self.m.calc_coleta_liquorica(df)
        self.assertEqual(r["casos_com_puncao"], 4)
        self.assertEqual(r["coleta_com_lead_time"], 4)
        self.assertEqual(r["coleta_le_1d_n"], 1)
        self.assertEqual(r["coleta_le_2d_n"], 2)
        self.assertAlmostEqual(r["pct_coleta_le_1d"], 25.0)
        self.assertAlmostEqual(r["pct_coleta_le_2d"], 50.0)
        self.assertAlmostEqual(r["p50_coleta_dias"], 3.0)
        self.assertAlmostEqual(r["p90_coleta_dias"], 7.5)

    def test_coleta_liquorica_sem_puncao(self):
        df = pd.DataFrame({
            "data_puncao_lombar_v17": [None, None],
            "lt_sintomas_coleta_dias_v17": [1, 2],
        })
        r = self.m.calc_coleta_liquorica(df)
        self.assertEqual(r["coleta_com_lead_time"], 0)
        self.assertTrue(math.isnan(r["pct_coleta_le_1d"]))

    def test_tempo_quimioprofilaxia(self):
        df = pd.DataFrame({
            "classificacao_agrupada_v17": [
                "Doença meningocócica", "Doença meningocócica",
                "Meningite por Hib/Hemófilo", "Meningite viral/asséptica",
            ],
            "lt_notificacao_quimioprofilaxia_dias_v17": [1, 5, 2, 1],
        })
        r = self.m.calc_tempo_quimioprofilaxia(df)
        self.assertEqual(r["elegiveis_dm_hib"], 3)
        self.assertEqual(r["quimio_com_lead_time"], 3)
        self.assertEqual(r["quimio_le_2d_n"], 2)
        self.assertAlmostEqual(r["pct_quimio_le_2d_entre_elegiveis"], 200 / 3)
        self.assertAlmostEqual(r["p50_quimio_dias"], 2.0)

    def test_sorogrupo_dm_confirmada(self):
        df = pd.DataFrame({
            "classificacao_agrupada_v17": ["Doença meningocócica"] * 3,
            "confirmado_v17": [1, 1, 0],
            "SeNMeningiditisEspecificarSorogrupo": ["C", "Ignorado", "B"],
        })
        r = self.m.calc_sorogrupo_dm(df)
        self.assertEqual(r["dm_confirmada_n"], 2)
        self.assertEqual(r["sorogrupo_preenchido_n"], 1)
        self.assertAlmostEqual(r["pct_sorogrupo_preenchido"], 50.0)

    def test_contatos_dm(self):
        df = pd.DataFrame({
            "classificacao_agrupada_v17": ["Doença meningocócica"] * 4 + ["Meningite viral/asséptica"],
            "NumeroComunicantes": [0, 5, 9, None, 40],
        })
        r = self.m.calc_contatos_dm(df)
        self.assertEqual(r["dm_n"], 4)
        self.assertEqual(r["dm_com_info_comunicantes"], 3)
        self.assertEqual(r["dm_zero_comunicantes"], 1)
        self.assertEqual(r["dm_sem_info_comunicantes"], 1)
        self.assertAlmostEqual(r["pct_dm_zero_ou_sem_info"], 50.0)
        self.assertAlmostEqual(r["p50_comunicantes_por_caso"], 5.0)

    def test_sem_denominador_populacional(self):
        df = pd.DataFrame({"tem_denominador_populacional_v17": [True, False, False, False]})
        r = self.m.calc_sem_denominador(df)
        self.assertEqual(r["sem_denominador_n"], 3)
        self.assertAlmostEqual(r["pct_sem_denominador"], 75.0)

    def test_oportunidade_deteccao(self):
        df = pd.DataFrame({"lt_sintomas_notificacao_dias_v17": [0, 1, 4, 10, -3, None]})
        r = self.m.calc_oportunidade_deteccao(df)
        self.assertEqual(r["com_lead_time"], 4)
        self.assertEqual(r["notificacao_le_1d_n"], 2)
        self.assertAlmostEqual(r["pct_notificacao_le_1d"], 50.0)
        self.assertAlmostEqual(r["p50_deteccao_dias"], 2.5)

    def test_completude_usa_campos_do_modulo_11(self):
        qual = importlib.import_module("11_qualidade_score_v20")
        self.assertEqual(self.m.CAMPOS_ESSENCIAIS, list(qual.CRITICAL_FIELDS))
        df = pd.DataFrame({
            "DataNotificacao": ["2024-01-01", "2024-01-02", None, None],
            "SexoPaciente": ["M", "F", "M", "F"],
        })
        r = self.m.calc_completude(df)
        self.assertEqual(r["campos_avaliados"], 2)
        # 50% em DataNotificacao e 100% em SexoPaciente → média 75%
        self.assertAlmostEqual(r["pct_completude_media"], 75.0)
        self.assertEqual(r["campo_pior"], "DataNotificacao")
        self.assertAlmostEqual(r["pct_campo_pior"], 50.0)

    def test_letalidade_padronizada(self):
        df = pd.DataFrame({
            "faixa_informe_v23": ["< 1 ano", "< 1 ano", "> 60 anos", "> 60 anos"],
            "confirmado_v17": [1, 1, 1, 1],
            "obito_meningite_v17": [1, 0, 0, 0],
        })
        pesos = pd.Series({"< 1 ano": 0.2, "> 60 anos": 0.8})
        r = self.m.calc_letalidade_padronizada(df, pesos)
        self.assertEqual(r["denominador_letalidade_n"], 4)
        self.assertEqual(r["obitos_n"], 1)
        self.assertAlmostEqual(r["letalidade_bruta_pct"], 25.0)
        # < 1 ano: 50% de letalidade (peso 0,2) · > 60: 0% (peso 0,8) → 10%
        self.assertAlmostEqual(r["letalidade_padronizada_pct"], 10.0)
        self.assertAlmostEqual(r["peso_coberto_pct"], 100.0)
        self.assertEqual(r["faixas_com_casos"], 2)

    def test_letalidade_padronizada_faixa_fora_do_padrao(self):
        """Faixa sem peso na população-padrão reduz a cobertura, sem quebrar o cálculo."""
        df = pd.DataFrame({
            "faixa_informe_v23": ["< 1 ano", "< 1 ano", "5 a 9 anos", "5 a 9 anos"],
            "confirmado_v17": [1, 1, 1, 1],
            "obito_meningite_v17": [1, 0, 1, 1],
        })
        pesos = pd.Series({"< 1 ano": 0.5, "> 60 anos": 0.5})
        r = self.m.calc_letalidade_padronizada(df, pesos)
        self.assertAlmostEqual(r["letalidade_padronizada_pct"], 50.0)
        self.assertAlmostEqual(r["peso_coberto_pct"], 50.0)
        self.assertEqual(r["faixas_com_casos"], 1)

    def test_escopos_incluem_estadual_e_regional(self):
        df = pd.DataFrame({
            "regional_v17": ["CUIABA", "CUIABA", "SINOP"],
            "ano_evento_v17": [2024, 2025, 2025],
            "tem_denominador_populacional_v17": [True, False, False],
        })
        wide = self.m._por_escopo(df, self.m.calc_sem_denominador)
        self.assertIn("ESTADUAL", set(wide["escopo"]))
        self.assertEqual(int((wide["escopo"] == "REGIONAL").sum()), 2)
        self.assertEqual(int((wide["escopo"] == "ANO").sum()), 2)
        estadual = wide[wide["escopo"] == "ESTADUAL"].iloc[0]
        self.assertEqual(int(estadual["casos_total"]), 3)


if __name__ == "__main__":
    unittest.main()
