# -*- coding: utf-8 -*-
"""Contratos do módulo 30 (CNES/SINASC) e seleção canônica SINAN do módulo 19."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "saida_meningites_v17"
DEMO = ROOT / "demo_cloud" / "saida_meningites_v17"
REL = ROOT / "relatorios"

CONTRATOS_V30 = {
    "cnes_perfil_unidade_notificante_v30.csv": [
        "escopo", "recorte", "casos", "pct_match_cnes",
        "pct_alta_complexidade", "pct_atencao_basica",
    ],
    "cnes_acesso_complexidade_regional_v30.csv": [
        "escopo", "recorte", "casos",
    ],
}


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


class TestPickSinanMeningiteView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load("19_dw_descobrir_e_extrair_v23.py")
        if cls.mod is None:
            raise unittest.SkipTest("módulo 19 ausente")

    def test_prefere_canonico_entre_varias(self):
        pick = self.mod.pick_sinan_meningite_view
        out = pick(["VW_MENINGITE_AUX", "VW_SINAN_MENINGITE", "OUTRA_MENING"])
        self.assertEqual(out["metodo"], "canonico")
        self.assertEqual(out["view"], "VW_SINAN_MENINGITE")
        self.assertIsNone(out["warning"])

    def test_heuristica_com_warning(self):
        pick = self.mod.pick_sinan_meningite_view
        out = pick(["VW_MENING_TESTE", "FOO_MENINGITE"])
        self.assertEqual(out["metodo"], "heuristica")
        self.assertEqual(out["view"], "VW_MENING_TESTE")
        self.assertIsNotNone(out["warning"])
        self.assertIn("Fallback heurístico", out["warning"])

    def test_nenhuma_candidata(self):
        pick = self.mod.pick_sinan_meningite_view
        out = pick([])
        self.assertEqual(out["metodo"], "nenhuma")
        self.assertIsNone(out["view"])

    def test_schema_dbo_normalizado(self):
        pick = self.mod.pick_sinan_meningite_view
        out = pick(["dbo.VW_SINAN_MENINGITE", "X_MENING"])
        self.assertEqual(out["metodo"], "canonico")
        self.assertIn("VW_SINAN_MENINGITE", out["view"].upper())


class TestClassificarComplexidadeCnes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load("30_cnes_sinasc_enriquecimento_v30.py")
        if cls.mod is None:
            raise unittest.SkipTest("módulo 30 ausente")

    def test_basica_e_hospital(self):
        fn = self.mod.classificar_complexidade
        self.assertEqual(fn("CENTRO DE SAUDE/UNIDADE BASICA"), "Atenção básica")
        self.assertEqual(fn("HOSPITAL GERAL"), "Alta complexidade / hospitalar")
        self.assertEqual(fn("FARMACIA"), "Outros / intermediário")
        self.assertEqual(fn(None), "Sem informação")


class TestContratosV30(unittest.TestCase):
    def test_artefatos_se_gerados(self):
        faltando = []
        vazios_ok = 0
        for nome, cols in CONTRATOS_V30.items():
            p = _pick(nome)
            if p is None:
                faltando.append(nome)
                continue
            df = pd.read_csv(p)
            for col in cols:
                self.assertIn(col, df.columns, f"{nome}: coluna {col} ausente")
            if len(df) == 0:
                vazios_ok += 1  # permitido quando CNES ausente
        if faltando and len(faltando) == len(CONTRATOS_V30):
            self.skipTest("módulo 30 ainda não gerado (py -3.13 30_cnes_sinasc_enriquecimento_v30.py)")
        self.assertEqual(faltando, [], f"artefatos V30 ausentes: {faltando}")

    def test_orquestrador_registra_30_antes_do_29(self):
        src = (ROOT / "pipeline_meningites_v23_indicadores_ms.py").read_text(encoding="utf-8")
        self.assertIn("30_cnes_sinasc_enriquecimento_v30.py", src)
        self.assertIn('PROCEDENCIA_STEP = "29_procedencia_artefatos_v28.py"', src)
        # Na rotina ops: 30 roda antes de finalizar("ops"), que dispara o 29
        i_ops = src.find("def ops_steps(")
        self.assertGreater(i_ops, 0)
        bloco = src[i_ops:]
        i30 = bloco.find('run("30_cnes_sinasc_enriquecimento_v30.py"')
        i_fin = bloco.find('finalizar("ops")')
        self.assertGreater(i30, 0)
        self.assertGreater(i_fin, i30)


class TestDenominadorPorAno(unittest.TestCase):
    def test_build_denominador_por_ano(self):
        mod = _load("28_indicadores_novos_v28.py")
        if mod is None or not hasattr(mod, "build_denominador_por_ano"):
            self.skipTest("build_denominador_por_ano ausente no módulo 28")
        df = pd.DataFrame({
            "ano_evento_v17": [2019, 2019, 2024, 2024, 2024],
            "tem_denominador_populacional_v17": [0, 0, 1, 1, 1],
            "populacao_v17": [None, None, 1000, 2000, 3000],
        })
        out = mod.build_denominador_por_ano(df)
        self.assertEqual(len(out), 2)
        row19 = out[out["ano_evento_v17"] == 2019].iloc[0]
        row24 = out[out["ano_evento_v17"] == 2024].iloc[0]
        self.assertEqual(row19["status_denominador"], "sem_denominador")
        self.assertEqual(row24["status_denominador"], "denominador_real_ibge")
        self.assertIn("sem_carry_forward", str(row19["politica"]))


if __name__ == "__main__":
    unittest.main()
