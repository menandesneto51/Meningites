# Extração DW — Meningites V23

**Quando:** 2026-07-27T11:38:21
**Host:** 10.15.1.50 · **DB:** Datawarehouse

## Views/tabelas candidatas (*MENING*)

- `VW_SINAN_MENINGITE`

## Extratos gerados em `entradas_linkage/`

- **gal_lacen_meningites**: 5835 linhas → `gal_lacen_meningites.csv`
- **sim_obitos_meningites**: 84 linhas → `sim_obitos_meningites.csv`
- **cnes_estabelecimentos**: 11697 linhas → `cnes_estabelecimentos.csv`
- **sinan_meningites_dw**: 6032 linhas → `sinan_meningites_dw.csv`
- **sinasc_dw**: 239157 linhas → `sinasc_dw.csv`

## Próximo passo

```bat
py -3.13 17_linkage_gal_lacen_sim_v23.py
```

Fontes reutilizadas dos projetos: ROBÔ SIVEP, Monitoramento ondas de calor, SIS Clima-Saúde.