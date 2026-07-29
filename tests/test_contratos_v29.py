# -*- coding: utf-8 -*-
"""Contratos V28/V29: procedência de artefatos, origem dos indicadores MS
e regra corrigida do óbito do SIM (evidência real de óbito)."""
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

PROCEDENCIA_COLS = ["arquivo", "modulo_origem", "gerado_em", "idade_horas", "linhas", "status"]
STATUS_VALIDOS = {"fresco", "atrasado", "ausente"}


def _pick(*candidates: Path) -> Path | None:
    for p in candidates:
        if p.exists():
            return p
    return None


def _load_module(nome_arquivo: str):
    """Importa módulo numerado (nome não é identificador Python válido)."""
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


class TestProcedenciaArtefatos(unittest.TestCase):
    def test_contrato_colunas(self):
        p = _pick(OUT / "procedencia_artefatos_v28.csv", DEMO / "procedencia_artefatos_v28.csv")
        if p is None:
            self.skipTest("procedencia_artefatos_v28.csv ainda não gerado (rode o módulo 29)")
        df = pd.read_csv(p)
        for col in PROCEDENCIA_COLS:
            self.assertIn(col, df.columns, f"coluna obrigatória ausente: {col}")
        self.assertGreater(len(df), 0)

    def test_status_dominio_e_tipos(self):
        p = _pick(OUT / "procedencia_artefatos_v28.csv", DEMO / "procedencia_artefatos_v28.csv")
        if p is None:
            self.skipTest("procedencia_artefatos_v28.csv ainda não gerado")
        df = pd.read_csv(p)
        fora = set(df["status"].astype(str).unique()) - STATUS_VALIDOS
        self.assertFalse(fora, f"status fora do domínio: {fora}")
        self.assertFalse(df["arquivo"].duplicated().any(), "arquivo deve ser único")
        idade = pd.to_numeric(df["idade_horas"], errors="coerce")
        self.assertTrue((idade.dropna() >= -1).all(), "idade_horas não pode ser negativa")
        ausentes = df[df["status"].astype(str).eq("ausente")]
        if not ausentes.empty:
            self.assertTrue(pd.to_numeric(ausentes["idade_horas"], errors="coerce").isna().all())

    def test_execucao_json(self):
        p = _pick(OUT / "pipeline_execucao_v28.json", DEMO / "pipeline_execucao_v28.json")
        if p is None:
            self.skipTest("pipeline_execucao_v28.json ainda não gerado (rode o orquestrador)")
        data = json.loads(p.read_text(encoding="utf-8"))
        self.assertIn("passos", data)
        self.assertGreater(len(data["passos"]), 0)
        for passo in data["passos"]:
            for campo in ["script", "obrigatorio", "status", "duracao_s", "erro"]:
                self.assertIn(campo, passo)
            self.assertIn(passo["status"], {"ok", "falhou", "pulado"})


class TestIndicadoresMSProcedencia(unittest.TestCase):
    def test_colunas_origem_e_data(self):
        p = _pick(OUT / "indicadores_ms_operacionais_v23.csv", DEMO / "indicadores_ms_operacionais_v23.csv")
        if p is None:
            self.skipTest("indicadores_ms_operacionais_v23.csv ausente")
        df = pd.read_csv(p)
        for col in ["modulo_origem", "gerado_em"]:
            self.assertIn(col, df.columns, f"indicador MS servido sem coluna {col}")
        origens = set(df["modulo_origem"].astype(str).unique())
        self.assertTrue(
            origens <= {"12_indicadores_ms_operacionais_v23.py", "26_indicadores_ops_avancados_v25.py"},
            f"origem inesperada: {origens}",
        )

    def test_copia_canonica_do_modulo_12(self):
        p = _pick(OUT / "indicadores_ms_operacionais_base_v23.csv")
        if p is None:
            self.skipTest("cópia canônica do módulo 12 ainda não gerada")
        df = pd.read_csv(p)
        self.assertIn("modulo_origem", df.columns)
        self.assertTrue(
            (df["modulo_origem"].astype(str) == "12_indicadores_ms_operacionais_v23.py").all(),
            "a cópia canônica não pode ser sobrescrita pelo módulo 26",
        )

    def test_referencia_nacional_datada(self):
        p = _pick(OUT / "indicadores_ms_operacionais_v23.csv", DEMO / "indicadores_ms_operacionais_v23.csv")
        if p is None:
            self.skipTest("indicadores_ms_operacionais_v23.csv ausente")
        df = pd.read_csv(p)
        for col in ["referencia_brasil_2024", "referencia_ano", "referencia_fonte"]:
            self.assertIn(col, df.columns)
        anos = pd.to_numeric(df["referencia_ano"], errors="coerce").dropna().unique()
        self.assertTrue(len(anos) == 1 and anos[0] >= 2024)


class TestObitoSimEvidencia(unittest.TestCase):
    """Match no SIM só vira óbito com data de óbito e/ou CID de meningite."""

    def setUp(self):
        self.mod = _load_module("20_enriquecimento_dw_fila_cievs_v23.py")
        if self.mod is None:
            self.skipTest("módulo 20 ausente")

    def test_cid_meningite(self):
        for cid in ["A39.0", "G00.9 Meningite bacteriana", "A87", "G03.9", "A17.0", "b37.5"]:
            self.assertTrue(self.mod.cid_meningite(cid), f"{cid} deveria ser compatível")
        for cid in ["", None, "I21.0", "C34.9", "ignorado", "J18.9"]:
            self.assertFalse(self.mod.cid_meningite(cid), f"{cid} não deveria ser compatível")

    def test_regra_em_dataframe_sintetico(self):
        enr = pd.DataFrame({
            "dw_sim_match_v23": [1, 1, 1, 1, 0],
            "dw_sim_cid_v23": ["A39.0", "", "I21.0", "G00.9", "A39.0"],
            "dw_sim_data_obito_v23": ["2024-03-10", "2024-05-02", "", "", "2024-01-01"],
        })
        flag, motivo = self.mod.classificar_obito_sim(enr)

        self.assertEqual(list(flag), [1, 1, 0, 1, 0])
        self.assertEqual(
            list(motivo),
            [
                "data_obito+cid_meningite",
                "data_obito",
                "match_sem_evidencia_obito",
                "cid_meningite",
                "sem_match_sim",
            ],
        )
        # o comportamento antigo (qualquer match = óbito) contaria 4
        self.assertEqual(int(enr["dw_sim_match_v23"].sum()), 4)
        self.assertEqual(int(flag.sum()), 3)

    def test_resumo_mortalidade_coerente(self):
        p = _pick(OUT / "mortalidade_sinan_sim_resumo_v23.csv")
        if p is None:
            self.skipTest("resumo de mortalidade SIM ainda não gerado")
        df = pd.read_csv(p)
        if "sim_matches_brutos" not in df.columns:
            self.skipTest("resumo gerado por versão anterior do módulo 20")
        r = df.iloc[0]
        self.assertLessEqual(int(r["obitos_sim_linkage"]), int(r["sim_matches_brutos"]))
        self.assertEqual(
            int(r["sim_matches_brutos"]) - int(r["obitos_sim_linkage"]),
            int(r["sim_matches_sem_evidencia_obito"]),
        )
        self.assertGreaterEqual(int(r["obitos_uniao_sinan_sim"]), int(r["obitos_sinan_evolucao"]))

    def test_desfechos_tem_motivo(self):
        p = _pick(OUT / "desfechos_mortalidade_sim_v23.csv")
        if p is None:
            self.skipTest("desfechos de mortalidade ainda não gerados")
        df = pd.read_csv(p, nrows=200)
        if "obito_sim_motivo_v23" not in df.columns:
            self.skipTest("desfechos gerados por versão anterior do módulo 20")
        self.assertIn("obito_sim_link_v23", df.columns)
        motivos = set(df["obito_sim_motivo_v23"].astype(str).unique())
        validos = {
            "sem_match_sim", "data_obito", "cid_meningite",
            "data_obito+cid_meningite", "match_sem_evidencia_obito",
        }
        self.assertTrue(motivos <= validos, f"motivos inesperados: {motivos - validos}")


class TestNomenclaturaNT154(unittest.TestCase):
    def test_score_nt154_com_alias(self):
        p = _pick(OUT / "score_risco_municipal_nt154_v25.csv")
        if p is None:
            self.skipTest("score NT154 ainda não gerado")
        df = pd.read_csv(p)
        self.assertIn("score_risco_nt154_v25", df.columns)
        # alias legado mantido enquanto o painel não migrar
        self.assertIn("score_risco_nt97_v25", df.columns)
        alias = _pick(OUT / "score_risco_municipal_nt97_v25.csv")
        self.assertIsNotNone(alias, "alias de compatibilidade deve continuar existindo")

    def test_surtos_nt154_com_alias(self):
        p = _pick(
            OUT / "alertas_inteligentes_surtos_nt154_v23.csv",
            DEMO / "alertas_inteligentes_surtos_nt154_v23.csv",
        )
        if p is None:
            self.skipTest("surtos NT154 ainda não gerados (rode o módulo 13)")
        alias = _pick(
            OUT / "alertas_inteligentes_surtos_nt97_v23.csv",
            DEMO / "alertas_inteligentes_surtos_nt97_v23.csv",
        )
        self.assertIsNotNone(alias, "alias legado dos surtos deve continuar existindo (painel)")
        self.assertEqual(list(pd.read_csv(p).columns), list(pd.read_csv(alias).columns))


if __name__ == "__main__":
    unittest.main()
