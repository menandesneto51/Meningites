# -*- coding: utf-8 -*-
"""Contratos mínimos dos artefatos operacionais (MS / fila / gestão V24)."""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "saida_meningites_v17"
DEMO = ROOT / "demo_cloud" / "saida_meningites_v17"
DEMO_REL = ROOT / "demo_cloud" / "relatorios"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _pick(*candidates: Path) -> Path | None:
    for p in candidates:
        if p.exists():
            return p
    return None


def _ler_csv(p: Path, **kw) -> pd.DataFrame:
    try:
        return pd.read_csv(p, low_memory=False, encoding="utf-8-sig", **kw)
    except UnicodeDecodeError:
        return pd.read_csv(p, low_memory=False, encoding="latin1", **kw)


def _e_texto(serie: pd.Series) -> bool:
    """`object` no pandas 2.x, `str` no pandas 3 — checar só `object` faz a
    varredura de texto livre passar vazia e o teste aprovar sem ter olhado nada."""
    return bool(pd.api.types.is_object_dtype(serie) or pd.api.types.is_string_dtype(serie))


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

    def test_backlog_v25(self):
        p = _pick(OUT / "backlog_operacional_resumo_v25.csv", DEMO / "backlog_operacional_resumo_v25.csv")
        if p is None:
            self.skipTest("backlog V25 ainda não gerado")
        df = pd.read_csv(p)
        for col in ["casos_abertos", "investigacao_atrasada", "quimio_pendente_dm_hib"]:
            self.assertIn(col, df.columns)

    def test_linkage_completude_v25(self):
        p = _pick(OUT / "linkage_completude_kpis_v25.csv", DEMO / "linkage_completude_kpis_v25.csv")
        if p is None:
            self.skipTest("linkage V25 ainda não gerado")
        df = pd.read_csv(p)
        self.assertIn("pct_match_gal", df.columns)
        self.assertTrue((df["escopo"].astype(str) == "ESTADUAL").any())

    def test_score_nt97_v25(self):
        p = _pick(OUT / "score_risco_municipal_nt97_v25.csv", DEMO / "score_risco_municipal_nt97_v25.csv")
        if p is None:
            self.skipTest("score NT97 V25 ainda não gerado")
        df = pd.read_csv(p)
        self.assertIn("score_risco_nt97_v25", df.columns)
        self.assertGreater(len(df), 10)

    def test_scrub_pii_heuristic(self):
        from preparar_pacote_cloud_demo import is_pii, scrub_df

        self.assertTrue(is_pii("NomePaciente"))
        self.assertTrue(is_pii("NumeroCartaoSUS"))
        self.assertTrue(is_pii("DataNascimento"), "data de nascimento deve sair do pacote")
        self.assertFalse(is_pii("municipio_v17"))
        self.assertFalse(is_pii("codigo_municipio_v17"))
        # Regressão: a heurística antiga usava a substring "sus" e removia esta
        # variável epidemiológica da base demo.
        self.assertFalse(is_pii("ContatoComCasoSuspeitoOuConfirmadoDeMeningite"))
        self.assertFalse(is_pii("casos_suspeitos"))
        df = pd.DataFrame({"NomePaciente": ["X"], "municipio_v17": ["Cuiabá"], "casos": [1]})
        out = scrub_df(df)
        self.assertNotIn("NomePaciente", out.columns)
        self.assertIn("municipio_v17", out.columns)

    def test_pseudonimo_nao_preserva_o_numero(self):
        from preparar_pacote_cloud_demo import pseudonimo, scrub_df

        p1 = pseudonimo("2365377")
        self.assertTrue(p1.startswith("CASO-"))
        self.assertNotIn("2365377", p1)
        self.assertEqual(p1, pseudonimo("2365377"), "pseudônimo deve ser estável no pacote")
        self.assertNotEqual(p1, pseudonimo("2365378"))
        self.assertEqual(pseudonimo(None), "")

        df = pd.DataFrame(
            {
                "id_caso": [382408],
                "territorio": ["JACIARA | caso 2365377"],
                "evidencia": ["Caso aberto há 6915 dia(s) (meta =60)"],
            }
        )
        out = scrub_df(df)
        self.assertNotIn("382408", str(out["id_caso"].iloc[0]))
        self.assertNotIn("2365377", str(out["territorio"].iloc[0]))
        # Contagem de dias em texto não pode ser confundida com número de caso.
        self.assertIn("6915", str(out["evidencia"].iloc[0]))


class TestLGPDPacoteDemo(unittest.TestCase):
    """O pacote demo_cloud é publicado no Streamlit Cloud: não pode conter
    identificador de caso nem quasi-identificador direto."""

    COL_PROIBIDA = re.compile(
        r"nomepaciente|nome_paciente|nomemae|nome_mae|nomepai|nomeobito|cartaosus|cartao_sus|"
        r"^datanascimento$|^anonascimento$|^mesnascimento$|logradouro|^endereco|^cep$|bairro|"
        r"telefone|email|geocampo",
        re.I,
    )
    COL_IDENTIFICADOR = {
        "NumeroNotificacao", "numero_notificacao", "id_caso", "sid", "_sid",
        "NumeroDO", "numero_do", "NumeroDN", "numero_dn",
    }
    # Pega também identificador com nome novo, criado por módulo futuro sem
    # atualizar a lista do gerador. Ancorado para não confundir com contagem
    # agregada (total_notificacoes) nem com código de município/ano.
    COL_ID_POR_PADRAO = re.compile(
        r"^(numero_?notifica\w*|nu_?notific\w*|id_?caso|caso_?id|_?sid|"
        r"numero_?d[on]|prontuario|chave_caso)$",
        re.I,
    )
    NUM_CRU = re.compile(r"^\s*\d{4,}\s*$")
    NUM_EM_TEXTO = re.compile(
        r"(?i)\b(casos?|notifica(?:c|ç)(?:a|ã)o|notif\.?)\s*(?:n[º°.]?\s*)?[:#]?\s*(\d{5,})\b"
    )

    @classmethod
    def setUpClass(cls):
        if not DEMO.exists():
            raise unittest.SkipTest("pacote demo_cloud ainda não gerado")
        cls.csvs = sorted(DEMO.glob("*.csv"))

    def test_sem_coluna_nominal_ou_data_de_nascimento(self):
        achados = []
        for p in self.csvs:
            df = _ler_csv(p, nrows=1)
            for c in df.columns:
                if self.COL_PROIBIDA.search(str(c)):
                    achados.append(f"{p.name}:{c}")
        self.assertEqual(achados, [], f"coluna identificável no pacote público: {achados}")

    def test_identificador_de_caso_pseudonimizado(self):
        achados = []
        for p in self.csvs:
            df = _ler_csv(p, nrows=500)
            for c in df.columns:
                nome = str(c)
                if nome not in self.COL_IDENTIFICADOR and not self.COL_ID_POR_PADRAO.search(nome):
                    continue
                brutos = [
                    v for v in df[c].dropna().astype(str).head(200)
                    if self.NUM_CRU.match(v)
                ]
                if brutos:
                    achados.append(f"{p.name}:{c} (ex.: {brutos[0]})")
        self.assertEqual(achados, [], f"identificador de caso sem pseudônimo: {achados}")

    def test_sem_numero_de_caso_em_texto_livre(self):
        achados = []
        for p in self.csvs:
            df = _ler_csv(p, nrows=1000)
            for c in df.columns:
                s = df[c]
                if not _e_texto(s):
                    continue
                for v in s.dropna().astype(str).head(500):
                    if self.NUM_EM_TEXTO.search(v):
                        achados.append(f"{p.name}:{c} -> {v[:60]}")
                        break
        self.assertEqual(achados, [], f"número de caso em texto livre: {achados}")

    def test_markdown_sem_numero_de_caso(self):
        alvos = list(DEMO_REL.glob("*.md")) + list(DEMO.glob("digests_regionais_v23/*.md"))
        if not alvos:
            self.skipTest("sem Markdown no pacote demo")
        achados = []
        for p in alvos:
            texto = p.read_text(encoding="utf-8", errors="ignore")
            m = self.NUM_EM_TEXTO.search(texto)
            if m:
                achados.append(f"{p.name} -> {m.group(0)}")
        self.assertEqual(achados, [], f"número de caso em Markdown público: {achados}")

    def test_relatorio_de_anonimizacao_presente(self):
        p = ROOT / "demo_cloud" / "ANONIMIZACAO.json"
        self.assertTrue(p.exists(), "ANONIMIZACAO.json ausente — pacote sem prestação de contas")
        data = json.loads(p.read_text(encoding="utf-8"))
        self.assertIn("politica", data)
        self.assertGreater(int(data.get("n_identificadores_pseudonimizados", 0)), 0)


if __name__ == "__main__":
    unittest.main()
