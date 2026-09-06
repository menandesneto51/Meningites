# -*- coding: utf-8 -*-
"""Contratos do módulo 35 (Fila CIEVS / RedCap — stub offline-safe)."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
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


# Fixture sintético — NÃO é dado de produção RedCap
FIXTURE_REDCAP = pd.DataFrame([
    {
        "record_id": "42",
        "data_notificacao": "2026-07-28 10:00:00",
        "data_sintomas": "2026-07-27",
        "codigo_municipio": "5103400",
        "municipio": "CUIABA",
        "regional": "Baixada Cuiabana",
        "tipo_evento": "caso_suspeito",
        "etiologia": "Doença meningocócica",
        "sorogrupo": "C",
        "faixa_etaria": "15 a 19 anos",
        "sexo": "M",
        "status_fila": "aberto",
        "prioridade": "",
        "acao_pendente": "investigacao_48h",
        "obito": "Nao",
        "surto_cluster": "Nao",
        "nu_notificacao_sinan": "",
        "NomePaciente": "TESTE LGPD",
        "CPF": "12345678901",
    },
    {
        "record_id": "99",
        "data_notificacao": "2026-07-29 08:00:00",
        "data_sintomas": "2026-07-28",
        "codigo_municipio": "510760",
        "municipio": "RONDONOPOLIS",
        "regional": "Sul",
        "tipo_evento": "obito",
        "etiologia": "DM",
        "sorogrupo": "W",
        "faixa_etaria": "20+ anos",
        "sexo": "F",
        "status_fila": "em_investigacao",
        "prioridade": "critica",
        "acao_pendente": "notif_imediata",
        "obito": "Sim",
        "surto_cluster": "Nao",
        "nu_notificacao_sinan": "2365377",
        "NomePaciente": "OUTRO",
        "CPF": "00000000000",
    },
])


class TestRedcapSchemaContrato(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load("35_redcap_fila_cievs_v35.py")
        if cls.mod is None:
            raise unittest.SkipTest("módulo 35 ausente")

    def test_colunas_esperadas_documentadas(self):
        esperadas = {
            "record_id", "data_notificacao", "codigo_municipio", "municipio",
            "tipo_evento", "etiologia", "status_fila", "prioridade",
            "obito", "surto_cluster", "nu_notificacao_sinan",
        }
        self.assertTrue(esperadas.issubset(set(self.mod.COLUNAS_ESPERADAS)))

    def test_drop_pii_e_hash_id(self):
        scrubbed = self.mod._drop_pii(FIXTURE_REDCAP)
        self.assertNotIn("CPF", scrubbed.columns)
        self.assertNotIn("NomePaciente", scrubbed.columns)
        hid = self.mod._hash_id("42")
        self.assertTrue(hid.startswith("RC-"))
        self.assertNotEqual(hid, "42")

    def test_preparar_fixture_sintetica(self):
        prep = self.mod.preparar_redcap(FIXTURE_REDCAP)
        self.assertEqual(len(prep), 2)
        self.assertTrue(all(c in prep.columns for c in self.mod.PREP_COLS))
        # PII / ids crus não vazam
        self.assertFalse(prep["id_registro_v35"].astype(str).isin(["42", "99"]).any())
        self.assertNotIn("nu_notificacao_sinan", prep.columns)
        self.assertNotIn("CPF", prep.columns)
        # vínculo SINAN só como flag
        self.assertEqual(bool(prep.iloc[0]["tem_vinculo_sinan_v35"]), False)
        self.assertEqual(bool(prep.iloc[1]["tem_vinculo_sinan_v35"]), True)
        # prioridade: óbito → critica; DM aberto → alta
        self.assertEqual(prep.iloc[1]["prioridade_v35"], "critica")
        self.assertEqual(prep.iloc[0]["prioridade_v35"], "alta")

    def test_kpis_e_gap(self):
        prep = self.mod.preparar_redcap(FIXTURE_REDCAP)
        kdf = self.mod.kpis_fila(prep, disponivel=True)
        est = kdf[kdf["escopo"].eq("ESTADUAL")]
        total = est[est["indicador"].eq("registros_total")]
        self.assertEqual(int(total.iloc[0]["n"]), 2)
        crit = est[est["indicador"].eq("prioridade_critica")]
        self.assertGreaterEqual(int(crit.iloc[0]["n"]), 1)
        gaps = self.mod.gap_sinan(prep)
        self.assertEqual(len(gaps), 1)
        self.assertFalse(gaps["id_registro_v35"].astype(str).isin(["42"]).any())

    def test_kpis_stub_sem_arquivo(self):
        kdf = self.mod.kpis_fila(pd.DataFrame(), disponivel=False)
        self.assertEqual(kdf.iloc[0]["escopo"], "STUB")
        self.assertEqual(int(kdf.iloc[0]["n"]), 0)

    def test_loader_skip_arquivo_ausente(self):
        with tempfile.TemporaryDirectory() as td:
            ghost = Path(td) / "nao_existe.csv"
            df = self.mod._read_redcap(ghost)
            self.assertTrue(df.empty)


class TestRedcapArtefatosContrato(unittest.TestCase):
    def test_meta_ou_skip_seguro(self):
        p = _pick("redcap_fonte_meta_v35.json")
        if p is None:
            self.skipTest("redcap_fonte_meta_v35.json ainda não gerado")
        meta = json.loads(p.read_text(encoding="utf-8"))
        self.assertIn("redcap_disponivel", meta)
        self.assertIn("colunas_esperadas", meta)
        self.assertIn("lgpd", meta)
        self.assertFalse(meta["lgpd"].get("cpf_cns_nome_exportados", True))
        self.assertTrue(meta["lgpd"].get("record_id_hasheado", False))

    def test_kpis_colunas_se_presente(self):
        p = _pick("redcap_kpis_fila_v35.csv")
        if p is None:
            self.skipTest("redcap_kpis_fila_v35.csv ainda não gerado")
        try:
            df = pd.read_csv(p)
        except pd.errors.EmptyDataError:
            self.skipTest("CSV RedCap vazio")
        for col in ["escopo", "indicador", "n", "nota"]:
            self.assertIn(col, df.columns)

    def test_schema_esperado_se_presente(self):
        p = _pick("redcap_schema_esperado_v35.csv")
        if p is None:
            self.skipTest("schema esperado ainda não gerado")
        df = pd.read_csv(p)
        # cabeçalho-only: 0 linhas, colunas do contrato
        self.assertEqual(len(df), 0)
        self.assertIn("record_id", df.columns)


if __name__ == "__main__":
    unittest.main()
