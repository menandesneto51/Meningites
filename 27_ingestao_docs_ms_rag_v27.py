# -*- coding: utf-8 -*-
"""
27_ingestao_docs_ms_rag_v27.py
Ingere documentos MS (docs_ms/) em chunks para a RAG do Assistente CIEVS.

Aceita .md / .txt (versionáveis) e .pdf (local; gitignored).
Saída: assistente_kb_docs_ms_v27.csv + meta JSON.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd

from meningites_v17_common import OUT, ROOT

DOCS_MS = ROOT / "docs_ms"
CATALOGO = DOCS_MS / "catalogo.json"
OUT_CSV = OUT / "assistente_kb_docs_ms_v27.csv"
OUT_META = OUT / "assistente_kb_docs_ms_meta_v27.json"

EXT_OK = {".md", ".txt", ".pdf"}
CHUNK_CHARS = 900
CHUNK_OVERLAP = 120


def _strip(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9\s]+", " ", s.lower()).strip()


def _load_catalogo() -> dict:
    if not CATALOGO.exists():
        return {"documentos": []}
    try:
        return json.loads(CATALOGO.read_text(encoding="utf-8"))
    except Exception:
        return {"documentos": []}


def _catalog_by_file(cat: dict) -> dict[str, dict]:
    out = {}
    for d in cat.get("documentos") or []:
        arq = str(d.get("arquivo") or "").replace("\\", "/")
        if arq:
            out[arq] = d
    return out


def _read_text_file(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except Exception:
            continue
    return ""


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except Exception:
            print(f"[AVISO] PDF ignorado (instale pypdf): {path.name}")
            return ""
    try:
        reader = PdfReader(str(path))
        parts = []
        for page in reader.pages:
            t = page.extract_text() or ""
            if t.strip():
                parts.append(t)
        return "\n\n".join(parts)
    except Exception as e:
        print(f"[AVISO] Falha ao ler PDF {path.name}: {e}")
        return ""


def _read_any(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".md", ".txt"}:
        return _read_text_file(path)
    if ext == ".pdf":
        return _read_pdf(path)
    return ""


def _split_by_headings(text: str) -> list[tuple[str, str]]:
    """Retorna lista (titulo_secao, corpo). Suporta Markdown e texto de PDF."""
    text = (text or "").replace("\r\n", "\n")
    lines = text.split("\n")
    sections: list[tuple[str, list[str]]] = []
    cur_title = "intro"
    buf: list[str] = []

    heading_md = re.compile(r"^(#{1,3})\s+(.+)$")
    # Ex.: "3.1. DEFINIÇÃO DE CASO" / "7. CONCLUSÃO"
    heading_num = re.compile(
        r"^(\d+(?:\.\d+){0,3}\.?)\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9][^\n]{3,140})$"
    )
    heading_caps = re.compile(r"^([A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9][A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9\s\-/]{8,120})$")

    def flush():
        nonlocal buf, cur_title
        body = "\n".join(buf).strip()
        if body:
            sections.append((cur_title, buf))
        buf = []

    for line in lines:
        s = line.strip()
        m = heading_md.match(s)
        if m:
            flush()
            cur_title = m.group(2).strip()
            continue
        m = heading_num.match(s)
        if m and len(s) < 160:
            flush()
            cur_title = f"{m.group(1)} {m.group(2)}".strip()
            continue
        if heading_caps.match(s) and not s.endswith("."):
            flush()
            cur_title = s.title() if s.isupper() else s
            continue
        buf.append(line)
    flush()
    if not sections and text.strip():
        sections = [("documento", text.split("\n"))]
    return [(t, "\n".join(b).strip()) for t, b in sections if "\n".join(b).strip()]


def _chunk_text(text: str, size: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", (text or "").strip())
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks = []
    i = 0
    n = len(text)
    while i < n:
        end = min(n, i + size)
        # tenta quebrar em parágrafo/espaço
        if end < n:
            cut = text.rfind("\n\n", i + size // 2, end)
            if cut < 0:
                cut = text.rfind(" ", i + size // 2, end)
            if cut > i:
                end = cut
        piece = text[i:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        i = max(end - overlap, i + 1)
    return chunks


def _infer_tema(rel: str, meta: dict) -> str:
    if meta.get("tema"):
        return str(meta["tema"])
    rel_l = rel.lower().replace("\\", "/")
    if "historico" in rel_l:
        return "historico"
    if "ses_mt" in rel_l:
        return "ses_mt"
    if "nt154" in rel_l or "nt_154" in rel_l:
        return "norma"
    if "guia" in rel_l:
        return "vigilancia"
    if "informe" in rel_l:
        return "indicadores"
    if "caderno" in rel_l or "sinan" in rel_l:
        return "sinan"
    return "docs_ms"


def _tags_from(meta: dict, title: str, body: str) -> str:
    base = str(meta.get("tags") or "")
    extra = _strip(f"{title} {body[:240]}")
    words = [w for w in extra.split() if len(w) > 3][:18]
    return (base + " " + " ".join(words)).strip()


def iter_source_files() -> list[Path]:
    if not DOCS_MS.exists():
        return []
    files = []
    for p in DOCS_MS.rglob("*"):
        if not p.is_file():
            continue
        if p.name.lower() in {"readme.md", "catalogo.json"}:
            continue
        if p.suffix.lower() not in EXT_OK:
            continue
        # ignora placeholders vazios de README em subpastas? ses_mt README tem conteúdo útil curto — ok indexar
        files.append(p)
    return sorted(files)


def build_chunks() -> list[dict]:
    cat = _load_catalogo()
    by_file = _catalog_by_file(cat)
    rows: list[dict] = []
    for path in iter_source_files():
        rel = path.relative_to(DOCS_MS).as_posix()
        meta = by_file.get(rel, {})
        raw = _read_any(path)
        if not raw.strip():
            continue
        vigente = bool(meta.get("vigente", "historicos/" not in rel))
        prioridade = int(meta.get("prioridade", 50 if vigente else 10))
        fonte = str(meta.get("fonte") or f"docs_ms/{rel}")
        titulo_doc = str(meta.get("titulo") or path.stem.replace("_", " "))
        tema = _infer_tema(rel, meta)
        doc_id = str(meta.get("id") or path.stem)

        for sec_title, sec_body in _split_by_headings(raw):
            for i, chunk in enumerate(_chunk_text(sec_body), start=1):
                cid = f"docsms_{doc_id}__{_slug(sec_title)}__{i}"
                titulo = f"{titulo_doc} — {sec_title}" if sec_title not in {"intro", "documento"} else titulo_doc
                # penaliza histórico na recuperação via tag + prioridade
                tags = _tags_from(meta, titulo, chunk)
                if not vigente:
                    tags = f"historico revogado nao-vigente {tags}"
                rows.append({
                    "id": cid,
                    "titulo": titulo[:220],
                    "tema": tema,
                    "tags": tags[:400],
                    "fonte": fonte,
                    "texto": chunk,
                    "vigente": vigente,
                    "prioridade": prioridade,
                    "arquivo": rel,
                    "origem": "docs_ms",
                })
    # ordena: vigentes / prioridade
    rows.sort(key=lambda r: (-int(r["vigente"]), -int(r["prioridade"]), r["id"]))
    return rows


def _slug(s: str) -> str:
    s = _strip(s)
    s = re.sub(r"\s+", "_", s)
    return (s[:48] or "sec").strip("_")


def load_docs_ms_chunks(prefer_fresh: bool = True) -> list[dict]:
    """
    Carrega chunks docs_ms para o assistente.
    Se prefer_fresh, tenta reprocessar a pasta; senão usa CSV em OUT.
    """
    if prefer_fresh and DOCS_MS.exists():
        try:
            return build_chunks()
        except Exception:
            pass
    if OUT_CSV.exists():
        try:
            df = pd.read_csv(OUT_CSV, encoding="utf-8-sig", low_memory=False)
            return df.to_dict(orient="records")
        except Exception:
            return []
    return []


def export() -> dict:
    OUT.mkdir(exist_ok=True)
    rows = build_chunks()
    pd.DataFrame(rows).to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    meta = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "n_chunks": len(rows),
        "n_arquivos": len({r["arquivo"] for r in rows}),
        "n_vigentes": sum(1 for r in rows if r.get("vigente")),
        "pasta": str(DOCS_MS),
        "arquivo_kb": OUT_CSV.name,
    }
    OUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def main():
    meta = export()
    print("[OK] Ingestão docs_ms RAG V27")
    print(f"  Arquivos: {meta['n_arquivos']} | Chunks: {meta['n_chunks']} | Vigentes: {meta['n_vigentes']}")
    print(f"  Saída: {OUT_CSV}")


if __name__ == "__main__":
    main()
