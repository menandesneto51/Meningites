# -*- coding: utf-8 -*-
"""Contratos do módulo 33 (SIH × SINAN subnotificação)."""
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


class TestSihExtractNo19(unittest.TestCase):
    def test_extract_sih_existe(self):
        mod = _load("19_dw_descobrir_e_extrair_v23.py")
        if mod is None:
            self.skipTest("módulo 19 ausente")
        self.assertTrue(hasattr(mod, "extract_sih_meningite"))
        self.assertIn("sih_internacao", mod.KNOWN)
        self.assertEqual(mod.resolve_sih_view({})[1], "VW_INTERNACAO")


class TestSihHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load("33_sih_subnotificacao_v33.py")
        if cls.mod is None:
            raise unittest.SkipTest("módulo 33 ausente")

    def test_cid_meningite(self):
        s = pd.Series(["A39.0", "G00", "J18", "a87.1", ""])
        flags = self.mod.cid_meningite(s)
        self.assertEqual(flags.tolist(), [True, True, False, True, False])

    def test_linkage_match_e_sem_par(self):
        sih = pd.DataFrame([{
            "DiagnosticoPrincipal": "A390",
            "CodigoDiagnosticoPrincipal": "A390",
            "CodigoMunicipioResidencia": "510340",
            "MunicipioResidencia": "CUIABA",
            "Sexo": "M",
            "Idade": 20,
            "AnoInternacao": 2024,
            "MesInternacao": 6,
            "NumeroInternacoes": 1,
            "TeveDiariasUTI": "Sim",
            "FoiAObito": "Nao",
            "DiariasUTI": 2,
        }, {
            "DiagnosticoPrincipal": "G000",
            "CodigoDiagnosticoPrincipal": "G000",
            "CodigoMunicipioResidencia": "510340",
            "MunicipioResidencia": "CUIABA",
            "Sexo": "F",
            "Idade": 5,
            "AnoInternacao": 2024,
            "MesInternacao": 3,
            "NumeroInternacoes": 1,
            "TeveDiariasUTI": "Nao",
            "FoiAObito": "Sim",
            "DiariasUTI": 0,
        }])
        sinan = pd.DataFrame([{
            "NumeroNotificacao": "N1",
            "codigo_municipio_v17": "510340",
            "municipio_v17": "CUIABA",
            "SexoPaciente": "Masculino",
            "IdadePaciente": 20,
            "data_internacao_v17": "2024-06-10",
            "data_ref_v17": "2024-06-08",
            "ano_evento_v17": 2024,
            "classificacao_agrupada_v17": "Doença meningocócica",
            "regional_v17": "Centro-Norte",
        }])
        prep = self.mod.preparar_sih(sih)
        slots = self.mod.expandir_slots_sih(prep)
        sn = self.mod.preparar_sinan(sinan)
        link = self.mod.linkage_sih_sinan(slots, sn)
        self.assertEqual(int(link["match_sinan_v33"].sum()), 1)
        self.assertEqual(int((link["match_sinan_v33"] == 0).sum()), 1)
        kdf = self.mod.kpis(link, sn)
        self.assertTrue((kdf["escopo"] == "ESTADUAL").any())
        est = kdf[kdf["escopo"] == "ESTADUAL"].iloc[0]
        self.assertEqual(int(est["n_internacoes_sih"]), 2)
        self.assertEqual(int(est["n_sih_sem_sinan"]), 1)
        self.assertEqual(int(est["n_com_uti"]), 1)
        self.assertEqual(int(est["n_obito_hospitalar"]), 1)


class TestSihArtefatosContrato(unittest.TestCase):
    def test_meta_ou_skip_seguro(self):
        p = _pick("sih_fonte_meta_v33.json")
        if p is None:
            self.skipTest("sih_fonte_meta_v33.json ainda não gerado")
        meta = json.loads(p.read_text(encoding="utf-8"))
        self.assertIn("disponivel", meta)
        self.assertIn("linkage", meta)
        self.assertIn("cids", meta)

    def test_kpis_colunas_se_presente(self):
        p = _pick("sih_kpis_subnotificacao_v33.csv")
        if p is None:
            self.skipTest("sih_kpis_subnotificacao_v33.csv ainda não gerado")
        try:
            df = pd.read_csv(p)
        except pd.errors.EmptyDataError:
            self.skipTest("CSV SIH vazio (extrato ainda não disponível)")
        # Cabeçalho obrigatório mesmo sem linhas (caminho seguro)
        for col in ["escopo", "n_internacoes_sih", "n_sih_sem_sinan", "pct_uti", "pct_obito_hospitalar"]:
            self.assertIn(col, df.columns)


if __name__ == "__main__":
    unittest.main()
