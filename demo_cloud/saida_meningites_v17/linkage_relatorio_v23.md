# Relatório de linkage GAL / LACEN / SIM — V23

**Gerado em:** 15/08/2026 08:15

## Prontidão das fontes

```
fonte               status                   arquivo  n_registros  n_matches                                                                                       acao
  gal                   OK  gal_lacen_meningites.csv         5803        581                                    Usar matches em alertas/confirmacao laboratorial/obitos
lacen OK_MESMO_ARQUIVO_GAL  gal_lacen_meningites.csv            0          0 LACEN já coberto por gal_lacen_meningites (VW_GAL); matches em linkage_matches_gal_v23.csv
  sim                   OK sim_obitos_meningites.csv           84        103                                    Usar matches em alertas/confirmacao laboratorial/obitos
```

## Proxy interno (SINAN)

```
 n_casos  proxy_lab_positivo  proxy_lab_positivo_pct  proxy_obitos_sinan  confirmados_sem_lab_positivo_proxy                                                                                                                      interpretacao
    5953                 972               16.327902                 394                                2845 Proxy interno a partir do SINAN (PCR/cultura/látex/CIE e evolução). Substituído/complementado quando GAL/LACEN/SIM forem linkados.
```

- Matches externos totais: **684**
- Pasta de entrada: `C:\Users\Menandesneto\OneDrive\CIEVS MT\Meningites\entradas_linkage`

## Próximos passos

1. Atualizar extratos DW: `py -3.13 19_dw_descobrir_e_extrair_v23.py`.
2. Rodar novamente `17_linkage_gal_lacen_sim_v23.py`.
3. Usar `linkage_matches_*` para reforçar confirmação laboratorial e óbitos.
