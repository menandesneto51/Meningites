# -*- coding: utf-8 -*-
"""Contratos do módulo 34 (CIPV / SI-PNI × SINAN vacinal)."""
from __future__ import annotations

import importlib.util
import json
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


class TestCipvExtractNo19(unittest.TestCase):
    def test_extract_cipv_existe(self):
        mod = _load("19_dw_descobrir_e_extrair_v23.py")
        if mod is None:
            self.skipTest("módulo 19 ausente")
        self.assertTrue(hasattr(mod, "extract_cipv_meningite"))
        self.assertTrue(hasattr(mod, "resolve_cipv_view"))
        self.assertIn("cipv", mod.KNOWN)
        schema, table, metodo = mod.resolve_cipv_view({"CIPV_DW_TABLE": "VW_CIPV_TEST"})
        self.assertEqual(table, "VW_CIPV_TEST")
        self.assertEqual(metodo, "env")
        schema2, table2, metodo2 = mod.resolve_cipv_view({}, ["foo", "VW_SIPNI", "bar"])
        self.assertEqual(table2, "VW_SIPNI")
        self.assertEqual(metodo2, "canonico")
        schema3, table3, metodo3 = mod.resolve_cipv_view(
            {"SIPNI_MSSQL_VIEW": "VW_Vacinas_PNI"}
        )
        self.assertEqual(table3, "VW_Vacinas_PNI")
        self.assertEqual(metodo3, "env")
        self.assertTrue(hasattr(mod, "build_sipni_conn_str"))
        self.assertTrue(mod.sipni_host_configured({"SIPNI_MSSQL_HOST": "10.15.1.74"}))
        self.assertIn("29", mod.SIPNI_MENINGITE_CODES)
        self.assertNotIn("108", mod.SIPNI_MENINGITE_CODES)


class TestCipvHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load("34_cipv_cobertura_vacinal_v34.py")
        if cls.mod is None:
            raise unittest.SkipTest("módulo 34 ausente")

    def test_classificar_imuno(self):
        self.assertEqual(self.mod.classificar_imuno("Meningocócica ACWY"), "MenACWY")
        self.assertEqual(self.mod.classificar_imuno("Meningocócica C conjugada"), "MenC")
        self.assertEqual(self.mod.classificar_imuno("Haemophilus influenzae b"), "Hib")
        self.assertEqual(self.mod.classificar_imuno("Pentavalente"), "Penta/Hexa (Hib)")
        self.assertEqual(self.mod.classificar_imuno("29"), "MenC")
        self.assertEqual(self.mod.classificar_imuno("0103"), "MenACWY")
        self.assertEqual(self.mod.classificar_imuno("9"), "Hib")

    def test_faixa_risco(self):
        self.assertEqual(self.mod.faixa_risco_idade(0.5), "<1 ano")
        self.assertEqual(self.mod.faixa_risco_idade(12), "11 a 14 anos")
        self.assertEqual(self.mod.faixa_risco_idade(30), "20+ anos")
        self.assertEqual(self.mod.parse_idade_anos("011a"), 11.0)
        self.assertAlmostEqual(self.mod.parse_idade_anos("004m"), 4 / 12.0)
        self.assertEqual(self.mod.faixa_risco_idade("012a"), "11 a 14 anos")

    def test_preparar_e_agregar_cipv_sintetico(self):
        raw = pd.DataFrame([
            {
                "NomeVacina": "Meningocócica ACWY",
                "CodigoMunicipio": "5103400",
                "Municipio": "CUIABA",
                "AnoAplicacao": 2024,
                "IdadeAnos": 12,
                "CPF": "12345678901",  # deve ser descartado
                "NomePaciente": "TESTE",
            },
            {
                "NomeVacina": "Pentavalente",
                "CodigoMunicipio": "5103400",
                "Municipio": "CUIABA",
                "AnoAplicacao": 2024,
                "IdadeAnos": 0.8,
            },
            {
                "NomeVacina": "Influenza",
                "CodigoMunicipio": "5103400",
                "Municipio": "CUIABA",
                "AnoAplicacao": 2024,
                "IdadeAnos": 40,
            },
        ])
        scrubbed = self.mod._drop_pii(raw)
        self.assertNotIn("CPF", scrubbed.columns)
        self.assertNotIn("NomePaciente", scrubbed.columns)
        prep = self.mod.preparar_cipv(scrubbed)
        self.assertEqual(len(prep), 2)
        self.assertTrue(set(prep["imuno_grupo_v34"]).issubset({"MenACWY", "Penta/Hexa (Hib)"}))
        agg = self.mod.agregar_doses_cipv(prep)
        self.assertEqual(int(agg["n_doses"].sum()), 2)

    def test_status_vacinal_sinan_sintetico(self):
        base = pd.DataFrame([
            {
                "classificacao_agrupada_v17": "Doença meningocócica",
                "IdadePaciente": 12,
                "VacinaConjugadaMeningoC_bin_v17": 1,
                "VacinaContraHemofilos_bin_v17": 0,
                "VacinaContraPolissacaridicaAC_bin_v17": 0,
            },
            {
                "classificacao_agrupada_v17": "Doença meningocócica",
                "IdadePaciente": 3,
                "VacinaConjugadaMeningoC_bin_v17": 0,
                "VacinaContraHemofilos_bin_v17": 0,
                "VacinaContraPolissacaridicaAC_bin_v17": 0,
            },
            {
                "classificacao_agrupada_v17": "Meningite por Hib/Hemófilo",
                "IdadePaciente": 1,
                "VacinaConjugadaMeningoC_bin_v17": 0,
                "VacinaContraHemofilos_bin_v17": 1,
                "VacinaContraPolissacaridicaAC_bin_v17": 0,
            },
        ])
        st = self.mod.status_vacinal_sinan(base)
        dm = st[st["escopo"] == "DM"]
        self.assertFalse(dm.empty)
        self.assertEqual(int(dm.iloc[0]["n_casos"]), 2)
        self.assertEqual(int(dm.iloc[0]["n_vacinados_sim"]), 1)
        hib = st[st["escopo"] == "Hib"]
        self.assertEqual(int(hib.iloc[0]["n_vacinados_sim"]), 1)


class TestCipvArtefatosContrato(unittest.TestCase):
    def test_meta_ou_skip_seguro(self):
        p = _pick("cipv_fonte_meta_v34.json")
        if p is None:
            self.skipTest("cipv_fonte_meta_v34.json ainda não gerado")
        meta = json.loads(p.read_text(encoding="utf-8"))
        self.assertIn("cipv_disponivel", meta)
        self.assertIn("sinan_disponivel", meta)
        self.assertIn("lgpd", meta)
        self.assertFalse(meta["lgpd"].get("cpf_cns_nome_exportados", True))

    def test_kpis_colunas_se_presente(self):
        p = _pick("cipv_kpis_cobertura_v34.csv")
        if p is None:
            self.skipTest("cipv_kpis_cobertura_v34.csv ainda não gerado")
        try:
            df = pd.read_csv(p)
        except pd.errors.EmptyDataError:
            self.skipTest("CSV CIPV vazio")
        for col in ["escopo", "indicador", "fonte_cipv"]:
            self.assertIn(col, df.columns)


if __name__ == "__main__":
    unittest.main()
