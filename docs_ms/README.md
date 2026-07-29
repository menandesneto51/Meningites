# Corpus normativo MS — RAG do Assistente CIEVS

Pasta de documentos do Ministério da Saúde (e correlatos) usados na aba **05 Assistente IA**.

## Como usar

1. Coloque aqui PDFs/Markdown/TXT oficiais (só meningites / vigilância).
2. Rode:

```bat
py -3.13 27_ingestao_docs_ms_rag_v27.py
py -3.13 16_assistente_cievs_v23.py
```

Ou o pipeline operacional (`--ops`), que já chama a ingestão antes do assistente.

3. No painel, abra **05 Assistente IA** e pergunte (ex.: surto, quimio, investigação).

## Organização recomendada

| Pasta | Uso |
|-------|-----|
| `vigentes/` | Normas em vigor (NT 154, Guia vigente, Informe, Caderno SINAN) |
| `historicos/` | Documentos revogados (ex. NT 97) — marcados como não vigentes |
| `ses_mt/` | Orientacões estaduais SES-MT (opcional) |

## Formatos aceitos

- `.md` / `.txt` — preferidos (versionáveis no Git)
- `.pdf` — aceitos **localmente** (estão no `.gitignore`; não sobem ao GitHub)

## Regras de qualidade

- Preferir **fonte oficial MS** com edição/ano no cabeçalho.
- Não misturar protocolo clínico hospitalar genérico sem vínculo com vigilância.
- NT **154/2024** tem prioridade sobre NT 97 e sobre a 6ª edição do GVS (revogada nos pontos retificados).
- Sempre validar resposta humana antes de comunicação oficial.

## Catálogo

Metadados em `catalogo.json` (id, título, vigência, prioridade). Arquivos sem entrada no catálogo ainda são indexados, com prioridade padrão.
