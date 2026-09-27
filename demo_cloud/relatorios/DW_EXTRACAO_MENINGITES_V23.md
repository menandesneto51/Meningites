# Extração DW — Meningites V23

**Quando:** 2026-09-27T10:07:25
**Host:** 10.15.1.50 · **DB:** Datawarehouse

## Views/tabelas candidatas (*MENING*)

- `VW_SINAN_MENINGITE`

**View SINAN escolhida:** `VW_SINAN_MENINGITE` (método=`canonico`)

## Extratos gerados em `entradas_linkage/`

- **gal_lacen_meningites**: 6146 linhas → `gal_lacen_meningites.csv`
- **sim_obitos_meningites**: 87 linhas → `sim_obitos_meningites.csv`
- **cnes_estabelecimentos**: 11697 linhas → `cnes_estabelecimentos.csv`
- **cnes_leitos**: 1232 linhas → `cnes_leitos.csv`
- **sih_internacoes_meningite**: 477 linhas → `sih_internacoes_meningite.csv`
- **cipv_doses_meningite**: 3829 linhas → `cipv_doses_meningite.csv`
- **sinan_meningites_dw**: 6094 linhas → `sinan_meningites_dw.csv`
- **sinasc_dw**: 209032 linhas → `sinasc_dw.csv`

## Próximo passo

```bat
py -3.13 17_linkage_gal_lacen_sim_v23.py
```

Fontes reutilizadas dos projetos: ROBÔ SIVEP, Monitoramento ondas de calor, SIS Clima-Saúde.