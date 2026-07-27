# -*- coding: utf-8 -*-
"""
meningites_v17_common.py
Funções comuns do Robô de Meningites V17 BI Epidemiológico.
"""

from __future__ import annotations

from pathlib import Path
import re
import unicodedata
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent


def _resolve_out_rel() -> tuple[Path, Path]:
    """Usa saídas locais; se ausentes (ex.: Streamlit Cloud), cai no pacote demo_cloud."""
    out = ROOT / "saida_meningites_v17"
    rel = ROOT / "relatorios"
    demo_out = ROOT / "demo_cloud" / "saida_meningites_v17"
    demo_rel = ROOT / "demo_cloud" / "relatorios"
    # marcadores de painel operacional
    markers = [
        "base_unica_meningites_v17.csv",
        "indicadores_ms_operacionais_v23.csv",
        "indicadores_gestao_semana_v24.csv",
    ]
    if any((out / m).exists() for m in markers):
        out.mkdir(exist_ok=True)
        rel.mkdir(exist_ok=True)
        return out, rel
    if demo_out.exists() and any((demo_out / m).exists() for m in markers):
        return demo_out, demo_rel if demo_rel.exists() else rel
    out.mkdir(exist_ok=True)
    rel.mkdir(exist_ok=True)
    return out, rel


OUT, REL = _resolve_out_rel()


MISSING = {"", "nan", "none", "null", "*em branco", "em branco", "ignorado", "ign", "na", "não informado", "nao informado"}

CLASS_DETALHADA = {
    "1": "Meningococcemia", "01": "Meningococcemia",
    "2": "Meningite meningocócica", "02": "Meningite meningocócica",
    "3": "Meningite meningocócica com meningococcemia", "03": "Meningite meningocócica com meningococcemia",
    "4": "Meningite tuberculosa", "04": "Meningite tuberculosa",
    "5": "Meningite por outras bactérias", "05": "Meningite por outras bactérias",
    "6": "Meningite não especificada", "06": "Meningite não especificada",
    "7": "Meningite viral/asséptica", "07": "Meningite viral/asséptica",
    "8": "Meningite por outra etiologia", "08": "Meningite por outra etiologia",
    "9": "Meningite por Hib/Hemófilo", "09": "Meningite por Hib/Hemófilo",
    "10": "Meningite por Pneumococo", "10.0": "Meningite por Pneumococo",
}

CLASS_AGRUPADA = {
    "1": "Doença meningocócica", "01": "Doença meningocócica",
    "2": "Doença meningocócica", "02": "Doença meningocócica",
    "3": "Doença meningocócica", "03": "Doença meningocócica",
    "4": "Meningite tuberculosa", "04": "Meningite tuberculosa",
    "5": "Meningite bacteriana/outras bactérias", "05": "Meningite bacteriana/outras bactérias",
    "6": "Meningite não especificada", "06": "Meningite não especificada",
    "7": "Meningite viral/asséptica", "07": "Meningite viral/asséptica",
    "8": "Outras etiologias", "08": "Outras etiologias",
    "9": "Meningite por Hib/Hemófilo", "09": "Meningite por Hib/Hemófilo",
    "10": "Meningite pneumocócica", "10.0": "Meningite pneumocócica",
}

EVOLUCAO_MAP = {
    "1": "Alta", "1.0": "Alta",
    "2": "Óbito por meningite", "2.0": "Óbito por meningite",
    "3": "Óbito por outra causa", "3.0": "Óbito por outra causa",
    "9": "Ignorado", "9.0": "Ignorado",
}

CLASS_CASO_MAP = {
    "1": "Confirmado", "1.0": "Confirmado",
    "2": "Descartado", "2.0": "Descartado",
    "8": "Meningite por outra etiologia", "8.0": "Meningite por outra etiologia",
    "9": "Ignorado", "9.0": "Ignorado",
}

VACINA_ETIOLOGIA = {
    "VacinaContraPolissacaridicaAC_bin_v17": ("Meningocócica polissacarídica A/C", ["Doença meningocócica"]),
    "VacinaContraPolissacaridicaBC_bin_v17": ("Meningocócica polissacarídica B/C", ["Doença meningocócica"]),
    "VacinaConjugadaMeningoC_bin_v17": ("Meningocócica C conjugada", ["Doença meningocócica"]),
    "VacinaContraBCG_bin_v17": ("BCG", ["Meningite tuberculosa"]),
    "VacinaContraHemofilos_bin_v17": ("Hib/Hemófilos", ["Meningite por Hib/Hemófilo"]),
    "VacinaContraPneumococo_bin_v17": ("Pneumocócica", ["Meningite pneumocócica"]),
    "VacinaContraTriplice_bin_v17": ("Tríplice bacteriana/DTP", []),
    "VacinaOutras_bin_v17": ("Outras vacinas", []),
}

LAB_COLS = {
    "ResultadoCulturaLiquor": "Cultura líquor",
    "ResultadoCulturaSangueSoro": "Cultura sangue/soro",
    "ResultadoCulturaPetequias": "Cultura petequias",
    "ResultadoCulturaEscarro": "Cultura escarro",
    "ResultadoBacterioscopiaLiquor": "Bacterioscopia líquor",
    "ResultadoCIELiquor": "CIE líquor",
    "ResultadoAglutinacaoLatexLiquor": "Látex líquor",
    "ResultadoIsolamentoViralLiquor": "Isolamento viral líquor",
    "ResultadoPCRLiquor": "PCR líquor",
    "ResultadoPCRSangueSoro": "PCR sangue/soro",
    "ResultadoPCRPetequias": "PCR petequias",
    "ResultadoPCREscarro": "PCR escarro",
}

def strip_accents(s: str) -> str:
    s = "" if pd.isna(s) else str(s)
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def text_key(s) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", strip_accents(s).upper()).strip()

def read_csv_smart(path: Path, dtype=None) -> pd.DataFrame:
    last = None
    for enc in ["utf-8-sig", "utf-8", "latin1", "cp1252"]:
        for sep in [",", ";", "\t", "|"]:
            try:
                df = pd.read_csv(path, encoding=enc, sep=sep, low_memory=False, dtype=dtype)
                if df.shape[1] > 1:
                    return df
            except Exception as e:
                last = e
    if last:
        raise last
    return pd.read_csv(path, low_memory=False, dtype=dtype)

def find_file(patterns):
    for pat in patterns:
        hits = sorted(ROOT.glob(pat))
        if hits:
            return hits[0]
    return None

def norm_code6(x):
    if pd.isna(x):
        return np.nan
    s = re.sub(r"\D", "", str(x))
    if len(s) >= 7:
        s = s[:6]
    return s if len(s) == 6 else np.nan

def simnao_bin(x):
    if pd.isna(x):
        return np.nan
    s = text_key(x)
    if s in {"1", "1 0", "SIM", "S", "TRUE", "VERDADEIRO"}:
        return 1
    if s in {"2", "2 0", "3", "3 0", "NAO", "N", "FALSE", "FALSO"}:
        return 0
    return np.nan

def decode_basic(x, mapping, default="Ignorado/em branco"):
    if pd.isna(x):
        return default
    raw = str(x).strip()
    if raw.lower() in MISSING:
        return default
    return mapping.get(raw, mapping.get(raw.upper(), raw))

def class_detalhada(x):
    if pd.isna(x):
        return "Ignorado/em branco"
    raw = str(x).strip()
    if raw.lower() in MISSING:
        return "Ignorado/em branco"
    return CLASS_DETALHADA.get(raw, CLASS_DETALHADA.get(raw.replace(",", "."), raw))

def class_agrupada(x, espec=None):
    raw = "" if pd.isna(x) else str(x).strip()
    raw_norm = raw.replace(",", ".")
    if raw_norm in CLASS_AGRUPADA:
        return CLASS_AGRUPADA[raw_norm]
    txt = text_key(str(raw) + " " + ("" if pd.isna(espec) else str(espec)))
    if not txt or txt.lower() in MISSING:
        return "Ignorado/em branco"
    if "MENINGOCOC" in txt or "MENINGITIDIS" in txt or "MENINGOCOCCEMIA" in txt:
        return "Doença meningocócica"
    if "VIRAL" in txt or "ASSEPTICA" in txt or "ASSETICA" in txt or "ENTEROVIRUS" in txt:
        return "Meningite viral/asséptica"
    if "FUNGI" in txt or "FUNGICA" in txt or "CRIPTOCOC" in txt or "CRYPTOCOC" in txt or "CANDIDA" in txt:
        return "Meningite fúngica"
    if "PNEUMOCOC" in txt or "PNEUMONIAE" in txt:
        return "Meningite pneumocócica"
    if "HIB" in txt or "HEMOFIL" in txt or "HAEMOPHIL" in txt:
        return "Meningite por Hib/Hemófilo"
    if "TUBERCUL" in txt:
        return "Meningite tuberculosa"
    if "BACTERI" in txt:
        return "Meningite bacteriana/outras bactérias"
    if "NAO ESPEC" in txt or "N ESPEC" in txt:
        return "Meningite não especificada"
    return "Outras etiologias"

def load_base_v17() -> pd.DataFrame:
    """Carrega base única; prefere Parquet e copia para TEMP se OneDrive travar."""
    import shutil
    import tempfile

    pq = OUT / "base_unica_meningites_v17.parquet"
    csv = OUT / "base_unica_meningites_v17.csv"
    df = None
    onedrive = "onedrive" in str(OUT).lower()

    def _read_via_temp(src: Path, kind: str):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td) / src.name
            shutil.copy2(src, tmp)
            if kind == "parquet":
                return pd.read_parquet(tmp)
            return pd.read_csv(tmp, encoding="utf-8-sig", low_memory=False)

    if pq.exists():
        try:
            df = _read_via_temp(pq, "parquet") if onedrive else pd.read_parquet(pq)
        except Exception:
            try:
                df = _read_via_temp(pq, "parquet")
            except Exception as e:
                print(f"[AVISO] Falha ao ler parquet ({e}); tentando CSV.")
    if df is None:
        if not csv.exists():
            raise FileNotFoundError("Base V17 ausente. Rode 00_base_unica_meningites_v17.py.")
        try:
            df = _read_via_temp(csv, "csv") if onedrive else pd.read_csv(csv, encoding="utf-8-sig", low_memory=False)
        except Exception:
            df = _read_via_temp(csv, "csv")
    if "data_ref_v17" in df.columns:
        df["data_ref_v17"] = pd.to_datetime(df["data_ref_v17"], errors="coerce")
    return attach_mortalidade_sim_v23(df)


def attach_mortalidade_sim_v23(df: pd.DataFrame) -> pd.DataFrame:
    """Anexa desfechos de mortalidade SINAN∪SIM gerados pelo módulo 20 (se existirem)."""
    path = OUT / "desfechos_mortalidade_sim_v23.csv"
    if df is None or df.empty or not path.exists():
        # Sem linkage: união = SINAN; SIM = 0
        if "obito_meningite_v17" in df.columns:
            sinan = pd.to_numeric(df["obito_meningite_v17"], errors="coerce").fillna(0).astype(int)
            if "obito_sim_link_v23" not in df.columns:
                df["obito_sim_link_v23"] = 0
            if "obito_meningite_uniao_v23" not in df.columns:
                df["obito_meningite_uniao_v23"] = sinan
            if "obito_sim_sem_sinan_v23" not in df.columns:
                df["obito_sim_sem_sinan_v23"] = 0
        return df

    try:
        m = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return df

    key = None
    for cand in ["NumeroNotificacao", "numero_notificacao"]:
        if cand in df.columns and cand in m.columns:
            key = cand
            break
    cols = [c for c in [
        "obito_sim_link_v23", "obito_meningite_uniao_v23", "obito_sim_sem_sinan_v23",
        "dw_sim_match_v23", "dw_sim_score_v23", "dw_sim_cid_v23",
    ] if c in m.columns]
    if not cols:
        return df

    out = df.copy()
    # remove versões anteriores para re-merge
    for c in cols:
        if c in out.columns:
            out = out.drop(columns=[c])

    if key is not None:
        left = out[key].astype(str).str.strip()
        right = m[key].astype(str).str.strip()
        m2 = m.copy()
        m2[key] = right
        m2 = m2.drop_duplicates(key, keep="first")
        out["_join_key"] = left
        m2 = m2.rename(columns={key: "_join_key"})
        out = out.merge(m2[["_join_key"] + cols], on="_join_key", how="left")
        out = out.drop(columns=["_join_key"])
    else:
        # fallback posicional se mesmos N
        if len(m) == len(out):
            for c in cols:
                out[c] = m[c].values

    sinan = pd.to_numeric(out.get("obito_meningite_v17"), errors="coerce").fillna(0).astype(int)
    if "obito_sim_link_v23" in out.columns:
        out["obito_sim_link_v23"] = pd.to_numeric(out["obito_sim_link_v23"], errors="coerce").fillna(0).astype(int)
    else:
        out["obito_sim_link_v23"] = 0
    if "obito_meningite_uniao_v23" not in out.columns:
        out["obito_meningite_uniao_v23"] = ((sinan == 1) | (out["obito_sim_link_v23"] == 1)).astype(int)
    else:
        out["obito_meningite_uniao_v23"] = pd.to_numeric(out["obito_meningite_uniao_v23"], errors="coerce").fillna(0).astype(int)
    if "obito_sim_sem_sinan_v23" not in out.columns:
        out["obito_sim_sem_sinan_v23"] = ((out["obito_sim_link_v23"] == 1) & (sinan == 0)).astype(int)
    else:
        out["obito_sim_sem_sinan_v23"] = pd.to_numeric(out["obito_sim_sem_sinan_v23"], errors="coerce").fillna(0).astype(int)
    return out

def fmt_num(x, nd=1):
    try:
        if pd.isna(x):
            return "NA"
        if abs(float(x) - round(float(x))) < 1e-9:
            return f"{int(round(float(x))):,}".replace(",", ".")
        return f"{float(x):.{nd}f}".replace(".", ",")
    except Exception:
        return str(x)

def interpret_p(p, alpha=0.05):
    if pd.isna(p):
        return "p-valor indisponível."
    if p < alpha:
        return f"p={p:.4f}: diferença/associação estatisticamente significativa ao nível de {alpha:.0%}."
    return f"p={p:.4f}: não há evidência estatística suficiente ao nível de {alpha:.0%}."

def practical_or(orv):
    if pd.isna(orv):
        return "Relevância prática não estimável."
    if orv < 0.67:
        return "Associação protetora de magnitude potencialmente relevante."
    if orv < 0.90:
        return "Associação protetora discreta/moderada."
    if orv <= 1.10:
        return "Efeito prático pequeno ou próximo da nulidade."
    if orv <= 1.50:
        return "Aumento moderado da chance do desfecho."
    return "Aumento expressivo da chance do desfecho; priorizar investigação."
