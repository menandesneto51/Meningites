# SIH × SINAN — subnotificação hospitalar V33

**Gerado em:** 05/09/2026 22:01

Sinal de vigilância: internações SIH com CID de meningite (A39/G00–G03/A87) confrontadas ao SINAN por heurística (município + sexo + idade ±1 + janela temporal). **Não substitui** investigação caso a caso; não há chave AIH↔NU_NOTIFICACAO no extrato.

**Status:** disponível — Extrato com 462 linhas · 462 slots de internação · fila SIH-sem-SINAN=274

## KPIs estaduais

  escopo recorte  n_internacoes_sih  n_match_sinan  n_sih_sem_sinan  pct_sih_sem_sinan  pct_match_sinan  n_com_uti   pct_uti  n_obito_hospitalar  pct_obito_hospitalar  n_casos_sinan  janela_dias  idade_tol
ESTADUAL      MT                462            188              274          59.307359        40.692641         98 21.212121                  34              7.359307         5953.0           30          1

## Por ano

escopo recorte  n_internacoes_sih  n_match_sinan  n_sih_sem_sinan  pct_sih_sem_sinan  pct_match_sinan  n_com_uti   pct_uti  n_obito_hospitalar  pct_obito_hospitalar  n_casos_sinan  janela_dias  idade_tol
   ANO    2021                 65             16               49          75.384615        24.615385          8 12.307692                   4              6.153846            NaN           30          1
   ANO    2022                 91             36               55          60.439560        39.560440         18 19.780220                   5              5.494505            NaN           30          1
   ANO    2023                108             46               62          57.407407        42.592593         25 23.148148                   9              8.333333            NaN           30          1
   ANO    2024                 87             46               41          47.126437        52.873563         22 25.287356                   9             10.344828            NaN           30          1
   ANO    2025                 73             31               42          57.534247        42.465753         18 24.657534                   6              8.219178            NaN           30          1
   ANO    2026                 38             13               25          65.789474        34.210526          7 18.421053                   1              2.631579            NaN           30          1

## Top municípios (SIH sem par SINAN)

 ano_internacao_v33 codigo_municipio_v33           municipio_v33  n_internacoes_sih  n_match_sinan  n_com_uti  n_obito_hospitalar  n_sih_sem_sinan  pct_sih_sem_sinan
               2026               510840           VARZEA GRANDE                  8              3          2                   0                5          62.500000
               2026               510800                 TAPURAH                  4              1          2                   0                3          75.000000
               2026               510267             CAMPO VERDE                  2              0          0                   0                2         100.000000
               2026               510510                   JUARA                  3              1          0                   0                2          66.666667
               2026               510792                 SORRISO                  3              1          0                   0                2          66.666667
               2026               150503          NOVO PROGRESSO                  1              0          0                   0                1         100.000000
               2026               510125              ARAPUTANGA                  1              0          0                   0                1         100.000000
               2026               510140                ARIPUANA                  1              0          0                   0                1         100.000000
               2026               510330                COMODORO                  1              0          0                   0                1         100.000000
               2026               510340                  CUIABA                  2              1          1                   0                1          50.000000
               2026               510385         GAUCHA DO NORTE                  1              0          0                   0                1         100.000000
               2026               510420              GUIRATINGA                  1              0          0                   0                1         100.000000
               2026               510624            NOVA UBIRATA                  1              0          0                   1                1         100.000000
               2026               510720              RIO BRANCO                  1              0          0                   0                1         100.000000
               2026               510760            RONDONOPOLIS                  4              3          1                   0                1          25.000000
               2026               510850                    VERA                  1              0          0                   0                1         100.000000
               2026               510627 NOVO HORIZONTE DO NORTE                  1              1          0                   0                0           0.000000
               2026               510730   SAO JOSE DO RIO CLARO                  1              1          0                   0                0           0.000000
               2026               510790                   SINOP                  1              1          1                   0                0           0.000000
               2025               510340                  CUIABA                 12              5          5                   1                7          58.333333

## Como regenerar

```bat
py -3.13 19_dw_descobrir_e_extrair_v23.py
py -3.13 33_sih_subnotificacao_v33.py
```
