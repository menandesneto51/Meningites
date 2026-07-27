# Fila CIEVS unificada — Meningites V23

**Gerado em:** 27/07/2026 11:39
**Matches usados (score ≥ 0.75):** GAL=415 · SIM=64

## Enriquecimento DW na base

- Casos com match GAL: **415**
- Casos com GAL positivo: **70**
- Casos com match SIM: **64**

## Alertas linkage DW: 29
## Alertas qualidade: 43
## Fila unificada: 257 itens

### Top 15 da fila

- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · JACIARA | caso 2365377 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · VILA RICA | caso 2376787 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · COCALINHO | caso 2336634 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · ALTO ARAGUAIA | caso 2362236 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · SANTO ANTONIO DO LEVERGER | caso 1146304 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · CUIABA | caso 1777019 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · DENISE | caso 2191077 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · JUARA | caso 2074968 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · VARZEA GRANDE | caso 2164165 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · SANTO ANTONIO DO LEVERGER | caso 2209995 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · PORTO DOS GAUCHOS | caso 2308306 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · JUARA | caso 2308041 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · ALTO ARAGUAIA | caso 2365378 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · CANARANA | caso 2644023 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · POXOREO | caso 1 — Revisar evolução/encerramento no SINAN e causa básica no SIM.

## Como atualizar

```powershell
py -3.13 19_dw_descobrir_e_extrair_v23.py
py -3.13 17_linkage_gal_lacen_sim_v23.py
py -3.13 13_alertas_inteligentes_v23.py
py -3.13 20_enriquecimento_dw_fila_cievs_v23.py
```
