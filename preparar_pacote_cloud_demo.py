# -*- coding: utf-8 -*-
"""
Gera demo_cloud/ com as saídas do painel sem dado identificável — para Streamlit Cloud.

Três camadas de proteção, aplicadas a TODOS os artefatos do pacote (não a um
subconjunto de nomes de arquivo):

1. colunas nominais, de contato/endereço e de data de nascimento são removidas;
2. identificadores de caso (NumeroNotificacao, id_caso, sid) viram pseudônimos
   irreversíveis — o sal é sorteado a cada execução e não é persistido, então o
   pseudônimo não volta ao número original nem comparando pacotes;
3. número de caso embutido em texto livre (colunas de texto e Markdown) é
   substituído pelo mesmo pseudônimo, preservando a leitura da fila.

A prestação de contas da anonimização fica em demo_cloud/ANONIMIZACAO.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
from pathlib import Path

import pandas as pd

from meningites_v17_common import OUT, REL, ROOT

DEST = ROOT / "demo_cloud" / "saida_meningites_v17"
DEST_REL = ROOT / "demo_cloud" / "relatorios"

# --------------------------------------------------------------------------
# Classificação de colunas
# --------------------------------------------------------------------------

# Nominais, contato e endereço — removidas do pacote.
COLS_NOMINAIS = {
    "NomePaciente", "NomeMaePaciente", "NomeMae", "NomePai", "NomeObito",
    "NumeroCartaoSUS", "Logradouro", "Endereco", "EnderecoNumero", "Numero",
    "EnderecoComplemento", "Complemento", "PontoReferencia",
    "Cep", "CEP", "BairroResidencia", "Bairro", "Bairro_Paciente",
    "GeoCampo1", "GeoCampo2", "Telefone", "Email",
    "CodigoUnidadeNotificacao", "UnidadeNotificacao",
}

# Data de nascimento: quasi-identificador forte junto com município e sexo.
# A idade e a faixa etária são preservadas, que é o que o painel usa.
COLS_NASCIMENTO = {
    "DataNascimento", "AnoNascimento", "MesNascimento", "DataNasc", "dt_nascimento",
}

# Identificadores de caso: pseudonimizados (mantêm o join entre artefatos).
COLS_IDENTIFICADOR = {
    "NumeroNotificacao", "numero_notificacao", "id_caso", "sid", "_sid",
    "NumeroDO", "numero_do", "NumeroDN", "numero_dn",
}

# Substrings de campo nominal. Deliberadamente específicas: a versão anterior
# usava "sus", que removia ContatoComCasoSuspeitoOuConfirmadoDeMeningite da base.
SUBSTR_NOMINAIS = (
    "nomepaciente", "nome_paciente", "nomemae", "nome_mae", "nomepai", "nome_pai",
    "nomeobito", "cartaosus", "cartao_sus", "logradouro", "endereco",
    "bairro", "telefone", "email", "geocampo",
)

# Prefixos de arquivo que não entram no pacote público:
# dumps de schema do DW, listas cruas de notificação e inventário de objetos SQL.
EXCLUIR_PREFIXOS = (
    "dw_schema_",
    "dw_objetos_descobertos",
    "auditoria_sinan_somente_",
)

# JSONs seguros (só contagens/metadados) que o painel e os testes leem.
JSON_PERMITIDOS = {
    "auditoria_sinan_fonte_v23.json",
    "assistente_meta_v23.json",
    "painel_epi_meta_v23.json",
    "pipeline_execucao_v28.json",
}

# Número de caso embutido em texto livre. Exige 5+ dígitos para não capturar ano
# ("casos 2024") e exige o dígito colado ao rótulo, para não capturar frases
# como "Caso aberto há 6915 dia(s)".
NUM_CASO_EM_TEXTO = re.compile(
    r"(?i)\b(casos?|notifica(?:c|ç)(?:a|ã)o|notif\.?)\s*(?:n[º°.]?\s*)?[:#]?\s*(\d{5,})\b"
)

# Linha de Markdown com campo nominal explícito.
LINHA_NOMINAL_MD = re.compile(
    r"(?i)\b(nome\s+do\s+paciente|nome\s+da\s+m[ãa]e|nomepaciente|cart[ãa]o\s+sus|\bcns\b)"
)

# --------------------------------------------------------------------------
# Pseudonimização
# --------------------------------------------------------------------------

# Sem o sal, o pseudônimo não volta ao número de notificação original. O padrão é
# sortear a cada execução; definir DEMO_PII_SALT (fora do repositório) mantém o
# pseudônimo estável entre pacotes e evita diff em todos os CSVs a cada geração.
_SAL = os.environ.get("DEMO_PII_SALT") or secrets.token_hex(16)
_CACHE_PSEUDO: dict[str, str] = {}


def pseudonimo(valor) -> str:
    """Pseudônimo estável dentro do pacote e irreversível fora dele."""
    s = str(valor).strip()
    if not s or s.lower() in {"nan", "none", "<na>", "nat"}:
        return ""
    if s not in _CACHE_PSEUDO:
        digest = hashlib.sha256(f"{_SAL}|{s}".encode("utf-8")).hexdigest()[:8].upper()
        _CACHE_PSEUDO[s] = f"CASO-{digest}"
    return _CACHE_PSEUDO[s]


def _substituir_num_caso(m: re.Match) -> str:
    """Troca "caso 2365377" pelo mesmo pseudônimo usado nas colunas de id, para
    que fila, alertas e boletim continuem cruzáveis entre si."""
    return pseudonimo(m.group(2))


# --------------------------------------------------------------------------
# Regras por coluna
# --------------------------------------------------------------------------


def is_pii(col: str) -> bool:
    """True quando a coluna deve ser REMOVIDA do pacote demo."""
    nome = str(col)
    if nome in COLS_NOMINAIS or nome in COLS_NASCIMENTO:
        return True
    c = nome.lower()
    if c.startswith(("municipio", "regional", "codigo_municipio")):
        return False
    return any(s in c for s in SUBSTR_NOMINAIS)


def is_identificador(col: str) -> bool:
    """True quando a coluna deve ser PSEUDONIMIZADA (e não removida)."""
    return str(col) in COLS_IDENTIFICADOR


def e_coluna_de_texto(serie: pd.Series) -> bool:
    """Aceita `object` (pandas 2.x) e o dtype `str` do pandas 3, senão a
    sanitização de texto livre passa batida sem erro nenhum."""
    return bool(
        pd.api.types.is_object_dtype(serie) or pd.api.types.is_string_dtype(serie)
    )


def scrub_df(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica as três camadas e devolve o DataFrame pronto para o pacote."""
    out, _ = sanitizar_df(df)
    return out


def sanitizar_df(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Devolve (df sanitizado, relatório do que foi alterado)."""
    relatorio: dict[str, list[str]] = {
        "colunas_removidas": [],
        "colunas_pseudonimizadas": [],
        "colunas_texto_sanitizadas": [],
    }

    remover = [c for c in df.columns if is_pii(str(c))]
    if remover:
        df = df.drop(columns=remover, errors="ignore")
        relatorio["colunas_removidas"] = [str(c) for c in remover]

    df = df.copy()

    for col in df.columns:
        if is_identificador(col):
            df[col] = df[col].map(pseudonimo)
            relatorio["colunas_pseudonimizadas"].append(str(col))

    for col in df.columns:
        serie = df[col]
        if not e_coluna_de_texto(serie):
            continue
        mask = serie.notna()
        if not bool(mask.any()):
            continue
        original = serie[mask].astype(str)
        novo = original.str.replace(NUM_CASO_EM_TEXTO, _substituir_num_caso, regex=True)
        if bool((novo != original).any()):
            df.loc[mask, col] = novo
            relatorio["colunas_texto_sanitizadas"].append(str(col))

    return df, relatorio


def sanitizar_texto(texto: str) -> str:
    """Sanitiza Markdown: remove linha nominal e pseudonimiza número de caso."""
    linhas = [ln for ln in texto.splitlines() if not LINHA_NOMINAL_MD.search(ln)]
    return NUM_CASO_EM_TEXTO.sub(_substituir_num_caso, "\n".join(linhas))


def _tem_residuo_identificador(texto: str) -> bool:
    return bool(NUM_CASO_EM_TEXTO.search(texto) or LINHA_NOMINAL_MD.search(texto))


# --------------------------------------------------------------------------
# Cópia
# --------------------------------------------------------------------------


def _ler_csv(src: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(src, low_memory=False, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(src, low_memory=False, encoding="latin1")


def copy_csv(name: str, scrub: bool = True) -> bool:
    """Copia um CSV de OUT para o pacote demo, sempre sanitizado."""
    src = OUT / name
    if not src.exists():
        return False
    DEST.mkdir(parents=True, exist_ok=True)
    if not scrub:
        shutil.copy2(src, DEST / name)
        return True
    df, rel = sanitizar_df(_ler_csv(src))
    if any(rel.values()):
        df.to_csv(DEST / name, index=False, encoding="utf-8-sig")
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

    copiados: list[str] = []
    pulados_grandes: list[str] = []
    excluidos: list[str] = []
    auditoria: dict[str, dict] = {}

    for src in sorted(OUT.glob("*.csv")):
        if src.name.startswith(EXCLUIR_PREFIXOS):
            excluidos.append(src.name)
            continue
        if src.stat().st_size > 25_000_000:
            pulados_grandes.append(src.name)
            continue
        df, rel = sanitizar_df(_ler_csv(src))
        if any(rel.values()):
            df.to_csv(DEST / src.name, index=False, encoding="utf-8-sig")
            auditoria[src.name] = {k: v for k, v in rel.items() if v}
        else:
            shutil.copy2(src, DEST / src.name)
        copiados.append(src.name)

    # Metadados em JSON que o painel e os testes de contrato leem.
    jsons = []
    for nome in sorted(JSON_PERMITIDOS):
        src = OUT / nome
        if not src.exists():
            continue
        texto = src.read_text(encoding="utf-8", errors="ignore")
        if _tem_residuo_identificador(texto):
            texto = sanitizar_texto(texto)
            auditoria[nome] = {"texto_sanitizado": True}
        (DEST / nome).write_text(texto, encoding="utf-8")
        jsons.append(nome)

    # Digests regionais em Markdown
    dig = OUT / "digests_regionais_v23"
    if dig.exists():
        dest_d = DEST / "digests_regionais_v23"
        dest_d.mkdir(parents=True, exist_ok=True)
        for f in sorted(dig.glob("DIGEST_*.md")):
            bruto = f.read_text(encoding="utf-8", errors="ignore")
            limpo = sanitizar_texto(bruto)
            if limpo != bruto:
                auditoria[f"digests_regionais_v23/{f.name}"] = {"texto_sanitizado": True}
            (dest_d / f.name).write_text(limpo, encoding="utf-8")

    # Relatórios e boletins em Markdown
    for md in sorted(REL.glob("*.md")):
        if md.stat().st_size >= 2_000_000:
            continue
        bruto = md.read_text(encoding="utf-8", errors="ignore")
        limpo = sanitizar_texto(bruto)
        if limpo != bruto:
            auditoria[f"relatorios/{md.name}"] = {"texto_sanitizado": True}
        (DEST_REL / md.name).write_text(limpo, encoding="utf-8")

    # Malha municipal simplificada para mapas no Cloud
    geo_ok = False
    try:
        from importlib import import_module
        geo_mod = import_module("25_exportar_geo_cloud_simplificado")
        geo_ok = geo_mod.main() == 0
    except Exception as e:
        print(f"[AVISO] Geo Cloud não gerado: {e}")

    meta = {
        "n_arquivos_csv": len(copiados),
        "n_arquivos_json": len(jsons),
        "excluidos_por_politica": excluidos,
        "pulados_grandes": pulados_grandes,
        "geojson_simplificado": geo_ok,
        "aviso": (
            "Pacote DEMO para avaliação pública/cloud. Colunas nominais, de endereço e de "
            "data de nascimento removidas; identificadores de caso pseudonimizados com sal "
            "sorteado por execução e não persistido. Sem acesso ao DW."
        ),
    }
    (ROOT / "demo_cloud" / "META.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (ROOT / "demo_cloud" / "ANONIMIZACAO.json").write_text(
        json.dumps(
            {
                "politica": {
                    "removidas": "colunas nominais, contato, endereço e data de nascimento",
                    "pseudonimizadas": sorted(COLS_IDENTIFICADOR),
                    "texto_livre": "número de caso com 5+ dígitos substituído por pseudônimo",
                    "arquivos_excluidos": list(EXCLUIR_PREFIXOS),
                },
                "n_identificadores_pseudonimizados": len(_CACHE_PSEUDO),
                "por_arquivo": auditoria,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (DEST / "MODO_DEMO_CLOUD.txt").write_text(
        "Este diretório é um espelho anonimizado para Streamlit Cloud.\n",
        encoding="utf-8",
    )

    print(f"[OK] demo_cloud pronto: {len(copiados)} CSVs + {len(jsons)} JSONs → {DEST}")
    print(f"[OK] identificadores pseudonimizados: {len(_CACHE_PSEUDO)}")
    print(f"[OK] arquivos sanitizados: {len(auditoria)} (detalhe em demo_cloud/ANONIMIZACAO.json)")
    if excluidos:
        print("[POLITICA] fora do pacote:", excluidos)
    if pulados_grandes:
        print("[AVISO] pulados por tamanho:", pulados_grandes)


if __name__ == "__main__":
    main()
