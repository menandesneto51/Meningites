# Fila CIEVS unificada — Meningites V23

**Gerado em:** 29/07/2026 12:37
**Matches usados (score ≥ 0.75):** GAL=415 · SIM=64

## Enriquecimento DW na base

- Casos com match GAL: **415**
- Casos com GAL positivo: **70**
- Casos com match SIM: **64**

## Mortalidade SINAN × SIM (para Odds Ratio)

- Óbitos SINAN (EvolucaoCaso): **395**
- Óbitos SIM (linkage ≥ 0.75 **com evidência de óbito**): **64** — de 64 matches; 0 descartados por não terem data de óbito nem CID de meningite
- União SINAN∪SIM (desfecho padrão dos OR): **415**
- SIM sem óbito meningite no SINAN: **20**

Arquivo: `desfechos_mortalidade_sim_v23.csv` · resumo: `mortalidade_sinan_sim_resumo_v23.csv`.

## Alertas linkage DW: 29
## Alertas qualidade: 43
## Fila unificada: 257 itens

### Top 15 da fila

- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · JACIARA | CASO-7654F73D — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · VILA RICA | CASO-8DC7E574 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · COCALINHO | CASO-06108C82 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · ALTO ARAGUAIA | CASO-987A52F3 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · SANTO ANTONIO DO LEVERGER | CASO-F2BEA0E7 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · CUIABA | CASO-47E2E02D — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · DENISE | CASO-0CC91ABC — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · JUARA | CASO-7DC15045 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · VARZEA GRANDE | CASO-9066EA04 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · SANTO ANTONIO DO LEVERGER | CASO-EC6CA0C0 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · PORTO DOS GAUCHOS | CASO-4DE4C08D — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · JUARA | CASO-8649C824 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · ALTO ARAGUAIA | CASO-F61A6975 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · CANARANA | CASO-3B942580 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · POXOREO | caso 1 — Revisar evolução/encerramento no SINAN e causa básica no SIM.

## Como atualizar

```powershell
py -3.13 19_dw_descobrir_e_extrair_v23.py
py -3.13 17_linkage_gal_lacen_sim_v23.py
py -3.13 13_alertas_inteligentes_v23.py
py -3.13 20_enriquecimento_dw_fila_cievs_v23.py
```