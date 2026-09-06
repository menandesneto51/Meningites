# Fila CIEVS unificada — Meningites V23

**Gerado em:** 15/08/2026 08:15
**Matches usados (score ≥ 0.75):** GAL=420 · SIM=64

## Enriquecimento DW na base

- Casos com match GAL: **420**
- Casos com GAL positivo: **72**
- Casos com match SIM: **64**

## Mortalidade SINAN × SIM (para Odds Ratio)

- Óbitos SINAN (EvolucaoCaso): **394**
- Óbitos SIM (linkage ≥ 0.75 **com evidência de óbito**): **64** — de 64 matches; 0 descartados por não terem data de óbito nem CID de meningite
- União SINAN∪SIM (desfecho padrão dos OR): **414**
- SIM sem óbito meningite no SINAN: **20**

Arquivo: `desfechos_mortalidade_sim_v23.csv` · resumo: `mortalidade_sinan_sim_resumo_v23.csv`.

## Alertas linkage DW: 28
## Alertas qualidade: 44
## Fila unificada: 257 itens

### Top 15 da fila

- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · VILA RICA | caso 2376787 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · DENISE | caso 2191077 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · COCALINHO | caso 2336634 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · ALTO ARAGUAIA | caso 2362236 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · CUIABA | caso 1777019 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · SANTO ANTONIO DO LEVERGER | caso 1146304 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · JUARA | caso 2074968 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · VARZEA GRANDE | caso 2164165 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · PORTO DOS GAUCHOS | caso 2308306 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · JUARA | caso 2308041 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · ALTO ARAGUAIA | caso 2365378 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · JACIARA | caso 2365377 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · SANTO ANTONIO DO LEVERGER | caso 2209995 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · POXOREO | caso 1 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · CAMPINAPOLIS | caso 2571375 — Revisar evolução/encerramento no SINAN e causa básica no SIM.

## Como atualizar

```powershell
py -3.13 19_dw_descobrir_e_extrair_v23.py
py -3.13 17_linkage_gal_lacen_sim_v23.py
py -3.13 13_alertas_inteligentes_v23.py
py -3.13 20_enriquecimento_dw_fila_cievs_v23.py
```
