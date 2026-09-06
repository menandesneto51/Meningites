# Fila CIEVS / RedCap — Meningites V35

**Gerado em:** 2026-09-05T22:01:16
**Status:** redcap_fila_meningite_cievs.csv ausente — stub V35 ativo (sem inventar fila). Deposite CSV ou defina REDCAP_FILA_CSV.

## Escopo

- Canal quase em tempo real da CIEVS-MT para meningites / DM (quando o export existir).
- Complementa a fila SINAN/GAL/SIM do módulo 20 — **não a substitui**.
- Stub offline-safe: ausência do CSV não falha o pipeline.
- LGPD: sem CPF/CNS/nome; `record_id` hasheado; NU_NOTIFICACAO só como flag.

**Export disponível:** não

## Colunas esperadas no CSV

- `record_id`
- `data_notificacao`
- `data_sintomas`
- `codigo_municipio`
- `municipio`
- `regional`
- `tipo_evento`
- `etiologia`
- `sorogrupo`
- `faixa_etaria`
- `sexo`
- `status_fila`
- `prioridade`
- `acao_pendente`
- `obito`
- `surto_cluster`
- `nu_notificacao_sinan`

## Como ativar

1. Exportar do RedCap CIEVS (projeto meningites) as colunas acima (ou aliases).
2. Remover PII desnecessária no export de origem.
3. Salvar em `C:/Users/Menandesneto/OneDrive/CIEVS MT/Meningites/entradas_linkage/redcap_fila_meningite_cievs.csv` **ou** definir `REDCAP_FILA_CSV`.
4. Rodar `py -3.13 35_redcap_fila_cievs_v35.py`.

## IndicaSUS (fora de escopo por enquanto)

IndicaSUS **não** está integrado neste projeto. Só será considerado se houver objeto/API útil que SINAN/SIH/CNES não cubram; até lá permanece adiado (ver `.env.example`).

## Stub ativo

Nenhum registro RedCap de meningites foi carregado. O painel mostra o bloco 'Fila CIEVS / RedCap' com esta mensagem. A fila unificada V23 (SINAN) continua válida na aba operacional.
