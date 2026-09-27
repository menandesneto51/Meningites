# SIH × SINAN — subnotificação hospitalar V33

**Gerado em:** 27/09/2026 10:12

Sinal de vigilância: internações SIH com CID de meningite (A39/G00–G03/A87) confrontadas ao SINAN por heurística (município + sexo + idade ±1 + janela temporal). **Não substitui** investigação caso a caso; não há chave AIH↔NU_NOTIFICACAO no extrato.

**Status:** disponível — Extrato com 477 linhas · 477 slots de internação · fila SIH-sem-SINAN=284

## KPIs estaduais

  escopo recorte  n_internacoes_sih  n_match_sinan  n_sih_sem_sinan  pct_sih_sem_sinan  pct_match_sinan  n_com_uti   pct_uti  n_obito_hospitalar  pct_obito_hospitalar  n_casos_sinan  janela_dias  idade_tol
ESTADUAL      MT                477            193              284          59.538784        40.461216         99 20.754717                  34              7.127883         6004.0           30          1

## Por ano

escopo recorte  n_internacoes_sih  n_match_sinan  n_sih_sem_sinan  pct_sih_sem_sinan  pct_match_sinan  n_com_uti   pct_uti  n_obito_hospitalar  pct_obito_hospitalar  n_casos_sinan  janela_dias  idade_tol
   ANO    2021                 65             16               49          75.384615        24.615385          8 12.307692                   4              6.153846            NaN           30          1
   ANO    2022                 91             36               55          60.439560        39.560440         18 19.780220                   5              5.494505            NaN           30          1
   ANO    2023                108             46               62          57.407407        42.592593         25 23.148148                   9              8.333333            NaN           30          1
   ANO    2024                 87             46               41          47.126437        52.873563         22 25.287356                   9             10.344828            NaN           30          1
   ANO    2025                 73             31               42          57.534247        42.465753         18 24.657534                   6              8.219178            NaN           30          1
   ANO    2026                 53             18               35          66.037736        33.962264          8 15.094340                   1              1.886792            NaN           30          1

## Top municípios (SIH sem par SINAN)

 ano_internacao_v33 codigo_municipio_v33        municipio_v33  n_internacoes_sih  n_match_sinan  n_com_uti  n_obito_hospitalar  n_sih_sem_sinan  pct_sih_sem_sinan
               2026               510840        VARZEA GRANDE                 10              4          2                   0                6          60.000000
               2026               510800              TAPURAH                  6              1          2                   0                5          83.333333
               2026               510267          CAMPO VERDE                  2              0          0                   0                2         100.000000
               2026               510420           GUIRATINGA                  2              0          0                   0                2         100.000000
               2026               510510                JUARA                  3              1          0                   0                2          66.666667
               2026               510760         RONDONOPOLIS                  5              3          1                   0                2          40.000000
               2026               510792              SORRISO                  3              1          0                   0                2          66.666667
               2026               150503       NOVO PROGRESSO                  1              0          0                   0                1         100.000000
               2026               510125           ARAPUTANGA                  1              0          0                   0                1         100.000000
               2026               510140             ARIPUANA                  1              0          0                   0                1         100.000000
               2026               510170      BARRA DO BUGRES                  1              0          0                   0                1         100.000000
               2026               510330             COMODORO                  1              0          0                   0                1         100.000000
               2026               510340               CUIABA                  5              4          1                   0                1          20.000000
               2026               510385      GAUCHA DO NORTE                  1              0          0                   0                1         100.000000
               2026               510562     MIRASSOL D OESTE                  2              1          0                   0                1          50.000000
               2026               510624         NOVA UBIRATA                  1              0          0                   1                1         100.000000
               2026               510630          PARANATINGA                  1              0          0                   0                1         100.000000
               2026               510718 RIBEIRAO CASCALHEIRA                  1              0          0                   0                1         100.000000
               2026               510720           RIO BRANCO                  1              0          0                   0                1         100.000000
               2026               510790                SINOP                  2              1          2                   0                1          50.000000

## Como regenerar

```bat
py -3.13 19_dw_descobrir_e_extrair_v23.py
py -3.13 33_sih_subnotificacao_v33.py
```