# -*- coding: utf-8 -*-
"""Contratos mínimos dos artefatos operacionais (MS / fila / gestão V24)."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "saida_meningites_v17"
DEMO = ROOT / "demo_cloud" / "saida_meningites_v17"


def _pick(*candidates: Path) -> Path | None:
    for p in candidates:
        if p.exists():
            return p
    return None


class TestContratosOps(unittest.TestCase):
    def test_indicadores_ms_colunas(self):
        p = _pick(OUT / "indicadores_ms_operacionais_v23.csv", DEMO / "indicadores_ms_operacionais_v23.csv")
        self.assertIsNotNone(p, "indicadores_ms_operacionais_v23.csv ausente")
        df = pd.read_csv(p)
        for col in ["indicador", "valor_pct", "semaforo", "numerador", "denominador"]:
            self.assertIn(col, df.columns)
        self.assertGreater(len(df), 3)
        self.assertTrue(df["indicador"].astype(str).str.contains("pct_").any())

    def test_fila_cievs_colunas(self):
        p = _pick(OUT / "fila_cievs_unificada_v23.csv", DEMO / "fila_cievs_unificada_v23.csv")
        self.assertIsNotNone(p, "fila_cievs_unificada_v23.csv ausente")
        df = pd.read_csv(p, nrows=50)
        for col in ["origem", "prioridade", "tipo", "territorio", "acao"]:
            self.assertIn(col, df.columns)
        # scrub: não deve trazer NomePaciente
        self.assertNotIn("NomePaciente", df.columns)

    def test_gestao_v24_colunas(self):
        p = _pick(OUT / "indicadores_gestao_semana_v24.csv", DEMO / "indicadores_gestao_semana_v24.csv")
        self.assertIsNotNone(p, "indicadores_gestao_semana_v24.csv ausente")
        df = pd.read_csv(p)
        for col in ["casos_nowcast_se", "status_sazonal", "fila_cievs_criticos_n", "acao_sugerida"]:
            self.assertIn(col, df.columns)
        self.assertEqual(len(df), 1)

    def test_auditoria_fonte_json(self):
        p = _pick(OUT / "auditoria_sinan_fonte_v23.json", DEMO / "auditoria_sinan_fonte_v23.json")
        self.assertIsNotNone(p, "auditoria_sinan_fonte_v23.json ausente")
        data = json.loads(p.read_text(encoding="utf-8"))
        self.assertTrue(data.get("fonte_escolhida") or data.get("fonte"))

    def test_mortalidade_sinan_sim_uniao(self):
        p = _pick(OUT / "mortalidade_sinan_sim_resumo_v23.csv", DEMO / "mortalidade_sinan_sim_resumo_v23.csv")
        if p is None:
            self.skipTest("resumo mortalidade SIM ainda não gerado no demo")
        df = pd.read_csv(p)
        self.assertIn("obitos_sinan_evolucao", df.columns)
        self.assertIn("obitos_uniao_sinan_sim", df.columns)
        r = df.iloc[0]
        self.assertGreaterEqual(int(r["obitos_uniao_sinan_sim"]), int(r["obitos_sinan_evolucao"]))

    def test_scrub_pii_heuristic(self):
        from preparar_pacote_cloud_demo import is_pii, scrub_df

        self.assertTrue(is_pii("NomePaciente"))
        self.assertTrue(is_pii("NumeroCartaoSUS"))
        self.assertFalse(is_pii("municipio_v17"))
        self.assertFalse(is_pii("codigo_municipio_v17"))
        df = pd.DataFrame({"NomePaciente": ["X"], "municipio_v17": ["Cuiabá"], "casos": [1]})
        out = scrub_df(df)
        self.assertNotIn("NomePaciente", out.columns)
        self.assertIn("municipio_v17", out.columns)


if __name__ == "__main__":
    unittest.main()
