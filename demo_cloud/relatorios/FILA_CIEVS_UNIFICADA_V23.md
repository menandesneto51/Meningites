# Fila CIEVS unificada — Meningites V23

**Gerado em:** 27/09/2026 10:11
**Matches usados (score ≥ 0.75):** GAL=293 · SIM=64

## Enriquecimento DW na base

- Casos com match GAL: **293**
- Casos com GAL positivo: **81**
- Casos com match SIM: **64**

## Mortalidade SINAN × SIM (para Odds Ratio)

- Óbitos SINAN (EvolucaoCaso): **398**
- Óbitos SIM (linkage ≥ 0.75 **com evidência de óbito**): **64** — de 64 matches; 0 descartados por não terem data de óbito nem CID de meningite
- União SINAN∪SIM (desfecho padrão dos OR): **418**
- SIM sem óbito meningite no SINAN: **20**

Arquivo: `desfechos_mortalidade_sim_v23.csv` · resumo: `mortalidade_sinan_sim_resumo_v23.csv`.

## Alertas linkage DW: 51
## Alertas qualidade: 44
## Fila unificada: 280 itens

### Top 15 da fila

- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · CANARANA | CASO-B7E8422D — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · JUARA | CASO-F6E5E119 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · SORRISO | CASO-19E41AE7 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · JUARA | CASO-16D2E7B2 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · VARZEA GRANDE | CASO-870CBC55 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · SANTO ANTONIO DO LEVERGER | CASO-D81C1D5A — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · CUIABA | CASO-667C0FB1 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · CAMPINAPOLIS | CASO-82FE0684 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · CAMPO NOVO DO PARECIS | CASO-A106D99D — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · SANTO ANTONIO DO LEVERGER | CASO-D2059BC9 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · COCALINHO | CASO-253F8613 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · DENISE | CASO-3CF60095 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · ALTO ARAGUAIA | CASO-F4B76590 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · VILA RICA | CASO-10D39B58 — Revisar evolução/encerramento no SINAN e causa básica no SIM.
- **Crítico** · Óbito no SIM sem desfecho meningite no SINAN · JACIARA | CASO-A7C38FBE — Revisar evolução/encerramento no SINAN e causa básica no SIM.

## Como atualizar

```powershell
py -3.13 19_dw_descobrir_e_extrair_v23.py
py -3.13 17_linkage_gal_lacen_sim_v23.py
py -3.13 13_alertas_inteligentes_v23.py
py -3.13 20_enriquecimento_dw_fila_cievs_v23.py
```