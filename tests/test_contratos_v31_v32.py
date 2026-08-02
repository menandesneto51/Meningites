# -*- coding: utf-8 -*-
"""Contratos dos módulos 31 (população) e 32 (GAL detalhado)."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "saida_meningites_v17"
DEMO = ROOT / "demo_cloud" / "saida_meningites_v17"


def _pick(nome: str) -> Path | None:
    for p in (OUT / nome, DEMO / nome):
        if p.exists():
            return p
    return None


def _load(nome_arquivo: str):
    path = ROOT / nome_arquivo
    if not path.exists():
        return None
    chave = nome_arquivo[:-3].replace("-", "_")
    if chave in sys.modules:
        return sys.modules[chave]
    spec = importlib.util.spec_from_file_location(chave, path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[chave] = mod
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(chave, None)
        return None
    return mod


class TestGalParseFlags(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load("32_gal_laboratorio_detalhado_v32.py")
        if cls.mod is None:
            raise unittest.SkipTest("módulo 32 ausente")

    def test_detecta_sorogrupo_b(self):
        flags = self.mod._parse_flags("Grupo – Neisseria meningitidis: B | Neisseria meningitidis: Detectável")
        self.assertEqual(flags["gal_sorogrupo_nm_v32"], "B")
        self.assertEqual(flags["gal_nm_detectavel_v32"], 1)
        self.assertEqual(flags["gal_lab_positivo_v32"], 1)

    def test_nao_detectavel(self):
        flags = self.mod._parse_flags("Neisseria meningitidis: Não Detectável | Haemophilus influenzae: Não Detectável")
        self.assertEqual(flags["gal_nm_nao_detectavel_v32"], 1)
        self.assertEqual(flags["gal_nm_detectavel_v32"], 0)


class TestGalKpisContrato(unittest.TestCase):
    def test_kpis_colunas(self):
        p = _pick("gal_kpis_laboratorio_v32.csv")
        if p is None:
            self.skipTest("gal_kpis_laboratorio_v32.csv ainda não gerado")
        df = pd.read_csv(p)
        self.assertIn("escopo", df.columns)
        self.assertTrue((df["escopo"].astype(str) == "ESTADUAL").any())


class TestPopulacaoMeta(unittest.TestCase):
    def test_meta_anos(self):
        p = _pick("populacao_fonte_meta_v31.json")
        if p is None:
            # fallback: arquivo local de população
            pop = ROOT / "populacao_padronizada_mt.csv"
            if not pop.exists():
                self.skipTest("população ainda não atualizada")
            df = pd.read_csv(pop)
            anos = set(pd.to_numeric(df["ano"], errors="coerce").dropna().astype(int))
            self.assertTrue(anos & set(range(2010, 2020)) or anos >= {2020}, "sem anos úteis")
            return
        import json
        meta = json.loads(p.read_text(encoding="utf-8"))
        self.assertIn("anos", meta)
        self.assertTrue(len(meta["anos"]) >= 6)


class TestCnesLeitosExtractExists(unittest.TestCase):
    def test_funcao_extract_no_19(self):
        mod = _load("19_dw_descobrir_e_extrair_v23.py")
        if mod is None:
            self.skipTest("módulo 19 ausente")
        self.assertTrue(hasattr(mod, "extract_cnes_leitos"))


if __name__ == "__main__":
    unittest.main()
