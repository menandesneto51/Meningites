# Relatorio Preliminar Executivo - Robo de Meningites

Gerado em: **2026-04-29 08:12:38**

## 1. Objetivo

Consolidar a execucao automatizada do pipeline de inteligencia epidemiologica para meningites, incluindo qualidade da informacao, indicadores, testes estatisticos, series temporais, predicoes, sobrevivencia e geoprocessamento.

## 2. Bases e saidas oficiais

| Finalidade | Pasta | Uso recomendado |
|---|---|---|
| Indicadores finais 2020-2025 | `saida_meningites_FINAL_2020_2025` | Incidencia, mortalidade, letalidade, mapas populacionais e comparacao municipal |
| Historico 2010-2026 | `saida_meningites_FINAL_2010_2026` | Tendencia, sazonalidade, canal endemico e predicao |

## 3. Auditoria automatica

| pasta | existe | data_auditoria | indicadores_linhas | populacao_preenchidos | populacao_ausentes | incidencia_100mil_preenchidos | incidencia_100mil_ausentes | mortalidade_100mil_preenchidos | mortalidade_100mil_ausentes | casos_total_indicadores | predicoes_linhas | predicoes_horizontes | ensemble_modelos | qualidade_linhas | testes_linhas | testes_significativos_p005 | moran_erro |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| saida_meningites_FINAL_2020_2025 | True | 2026-04-29 08:12:38 | 513 | 513 | 0 | 513 | 0 | 513 | 0 | 1189.0 | 112 | 15d, 30d, 60d, 7d | 8 | 156 | 123 | 45 | No module named 'esda' |
| saida_meningites_FINAL_2010_2026 | True | 2026-04-29 08:12:38 | 1823 | 513 | 1310 | 513 | 1310 | 513 | 1310 | 4344.0 | 112 | 15d, 30d, 60d, 7d | 8 | 156 | 124 | 62 | No module named 'esda' |

## 4. Sintese executiva - 2020-2025

# Sumário executivo — Robô Meningites

## Escopo
Período analisado: 2020-01-05 a 2025-12-28  
Registros analisados: 1189

## Indicadores centrais
- Casos confirmados: 536
- Internações registradas: 1078
- Óbitos por meningite: 91
- Letalidade bruta entre confirmados: 16.98%

## Achados estatísticos prioritários
- ClassificacaoCaso ~ DoencasPreexistentesAIDS_bin: p=2.181e-07; associação estatisticamente significativa; efeito pequeno.
- ClassificacaoCaso ~ SinaisESintomasOutros_bin: p=1.933e-05; associação estatisticamente significativa; efeito pequeno.
- ClassificacaoCaso ~ SinaisESintomasCefaleia_bin: p=8.528e-05; associação estatisticamente significativa; efeito pequeno.
- ClassificacaoCaso ~ FaixaEtaria: p=0.0009104; associação estatisticamente significativa; efeito pequeno.
- ClassificacaoCaso ~ SexoPaciente: p=0.00327; associação estatisticamente significativa; efeito pequeno.
- ClassificacaoCaso ~ SinaisESintomasVomitos_bin: p=0.005533; associação estatisticamente significativa; efeito muito pequeno.
- ClassificacaoCaso ~ DoencasPreexistentesTraumatismo_bin: p=0.009405; associação estatisticamente significativa; efeito muito pequeno.
- ClassificacaoCaso ~ VacinaContraBCG_bin: p=0.01284; associação estatisticamente significativa; efeito pequeno.
- ClassificacaoCaso ~ DoencasPreexistentesTuberculose_bin: p=0.01315; associação estatisticamente significativa; efeito muito pequeno.
- ClassificacaoCaso ~ SinaisESintomasConvulsoes_bin: p=0.02096; associação estatisticamente significativa; efeito muito pequeno.

## Séries temporais
Ensemble gerado com até 8 modelos disponíveis no ambiente.

## Leitura para tomada de decisão
1. Priorizar correção de duplicidades e incompletude de campos críticos antes de inferências causais.
2. Interpretar OR como associação ajustada, não causalidade direta.
3. Integrar população IBGE e shapefile municipal para incidência, mortalidade, Moran e municípios silenciosos.
4. Utilizar canal endêmico e ensemble preditivo como triagem operacional, com validação epidemiológica antes de alertas formais.


## 5. Sintese executiva - 2010-2026

# Sumário executivo — Robô Meningites

## Escopo
Período analisado: 2010-01-01 a 2026-03-29  
Registros analisados: 4344

## Indicadores centrais
- Casos confirmados: 2542
- Internações registradas: 3907
- Óbitos por meningite: 321
- Letalidade bruta entre confirmados: 12.63%

## Achados estatísticos prioritários
- ClassificacaoCaso ~ SinaisESintomasCefaleia_bin: p=9.006e-23; associação estatisticamente significativa; efeito pequeno.
- ClassificacaoCaso ~ SinaisESintomasVomitos_bin: p=1.79e-18; associação estatisticamente significativa; efeito pequeno.
- ClassificacaoCaso ~ SinaisESintomasRigidezNuca_bin: p=1.682e-11; associação estatisticamente significativa; efeito pequeno.
- ClassificacaoCaso ~ VacinaContraBCG_bin: p=5.53e-11; associação estatisticamente significativa; efeito pequeno.
- ClassificacaoCaso ~ DoencasPreexistentesAIDS_bin: p=2.262e-09; associação estatisticamente significativa; efeito pequeno.
- ClassificacaoCaso ~ SinaisESintomasFebre_bin: p=6.55e-08; associação estatisticamente significativa; efeito muito pequeno.
- ClassificacaoCaso ~ VacinaConjugadaMeningoC_bin: p=1.591e-07; associação estatisticamente significativa; efeito pequeno.
- ClassificacaoCaso ~ SexoPaciente: p=5.908e-07; associação estatisticamente significativa; efeito muito pequeno.
- ClassificacaoCaso ~ RacaPaciente: p=6.172e-07; associação estatisticamente significativa; efeito muito pequeno.
- ClassificacaoCaso ~ VacinaContraPneumococo_bin: p=8.223e-07; associação estatisticamente significativa; efeito pequeno.

## Séries temporais
Ensemble gerado com até 8 modelos disponíveis no ambiente.

## Leitura para tomada de decisão
1. Priorizar correção de duplicidades e incompletude de campos críticos antes de inferências causais.
2. Interpretar OR como associação ajustada, não causalidade direta.
3. Integrar população IBGE e shapefile municipal para incidência, mortalidade, Moran e municípios silenciosos.
4. Utilizar canal endêmico e ensemble preditivo como triagem operacional, com validação epidemiológica antes de alertas formais.


## 6. Interpretacao tecnica recomendada

- Usar `saida_meningites_FINAL_2020_2025` como fonte principal para indicadores com denominador populacional.
- Usar `saida_meningites_FINAL_2010_2026` para tendencia historica, sazonalidade, canal endemico e predicao.
- Interpretar associacoes estatisticas como associacao observacional, nao causalidade direta.
- Validar duplicidades, incompletude e inconsistencias antes de publicacao formal.
- Se `moran_error.txt` indicar ausencia de `esda`, instalar `esda` depois ou documentar que Moran nao foi executado nesta rodada.

