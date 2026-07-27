# -*- coding: utf-8 -*-
"""
Gera demo_cloud/ com saídas do painel, sem dados nominais — para Streamlit Cloud.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

from meningites_v17_common import OUT, REL, ROOT

DEST = ROOT / "demo_cloud" / "saida_meningites_v17"
DEST_REL = ROOT / "demo_cloud" / "relatorios"

# Colunas nominais / endereço / identificadores diretos
PII_EXACT = {
    "NomePaciente", "NomeMaePaciente", "NumeroCartaoSUS", "NumeroNotificacao",
    "Logradouro", "EnderecoNumero", "EnderecoComplemento", "PontoReferencia",
    "Cep", "BairroResidencia", "GeoCampo1", "GeoCampo2",
    "CodigoUnidadeNotificacao", "UnidadeNotificacao",
}
PII_SUBSTR = ("nome", "mae", "cartao", "sus", "endereco", "logradouro", "cep", "bairro", "geo")


def is_pii(col: str) -> bool:
    if col in PII_EXACT:
        return True
    c = col.lower()
    return any(s in c for s in PII_SUBSTR) and not c.startswith(("municipio", "regional", "codigo_municipio"))


def scrub_df(df: pd.DataFrame) -> pd.DataFrame:
    drop = [c for c in df.columns if is_pii(str(c))]
    return df.drop(columns=drop, errors="ignore")


def copy_csv(name: str, scrub: bool = False) -> bool:
    src = OUT / name
    if not src.exists():
        return False
    DEST.mkdir(parents=True, exist_ok=True)
    if scrub or name.startswith("base_unica") or "alerta" in name.lower() or "fila" in name.lower():
        try:
            df = pd.read_csv(src, low_memory=False, encoding="utf-8-sig")
        except Exception:
            df = pd.read_csv(src, low_memory=False, encoding="latin1")
        scrub_df(df).to_csv(DEST / name, index=False, encoding="utf-8-sig")
    else:
        shutil.copy2(src, DEST / name)
    return True


def _clear_dir(path: Path) -> None:
    """Remove conteúdo com tolerância a locks do OneDrive/Windows."""
    if not path.exists():
        return
    for child in sorted(path.rglob("*"), reverse=True):
        try:
            if child.is_file() or child.is_symlink():
                child.unlink(missing_ok=True)
            elif child.is_dir():
                child.rmdir()
        except OSError:
            pass
    try:
        path.rmdir()
    except OSError:
        pass


def main():
    _clear_dir(DEST)
    _clear_dir(DEST_REL)
    DEST.mkdir(parents=True, exist_ok=True)
    DEST_REL.mkdir(parents=True, exist_ok=True)

    # Tudo que o dashboard costuma ler
    patterns = [
        "*.csv",
    ]
    copied = []
    skipped = []
    for pat in patterns:
        for src in sorted(OUT.glob(pat)):
            # evita dumps enormes irrelevantes ao painel
            if src.stat().st_size > 25_000_000:
                skipped.append(src.name)
                continue
            scrub = src.name.startswith("base_unica") or any(
                k in src.name.lower() for k in ("alerta", "fila", "enriquecimento_casos", "linkage_fila")
            )
            ok = copy_csv(src.name, scrub=scrub)
            if ok:
                copied.append(src.name)

    # digests (markdown) — só índice/resumo se existirem pastas
    dig = OUT / "digests_regionais_v23"
    if dig.exists():
        dest_d = DEST / "digests_regionais_v23"
        dest_d.mkdir(parents=True, exist_ok=True)
        for f in dig.glob("DIGEST_*.md"):
            text = f.read_text(encoding="utf-8", errors="ignore")
            # remove linhas com possível nominal (heurística leve)
            lines = [ln for ln in text.splitlines() if "Nome" not in ln and "CNS" not in ln]
            (dest_d / f.name).write_text("\n".join(lines), encoding="utf-8")

    for md in REL.glob("*.md"):
        if md.stat().st_size < 2_000_000:
            shutil.copy2(md, DEST_REL / md.name)

    meta = {
        "n_arquivos_csv": len(copied),
        "pulados_grandes": skipped,
        "aviso": (
            "Pacote DEMO para avaliação pública/cloud. "
            "Colunas nominais removidas da base e filas. Sem acesso ao DW."
        ),
    }
    (ROOT / "demo_cloud" / "META.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (DEST / "MODO_DEMO_CLOUD.txt").write_text(
        "Este diretório é um espelho anonimizado para Streamlit Cloud.\n",
        encoding="utf-8",
    )
    print(f"[OK] demo_cloud pronto: {len(copied)} CSVs → {DEST}")
    if skipped:
        print("[AVISO] pulados por tamanho:", skipped)


if __name__ == "__main__":
    main()
