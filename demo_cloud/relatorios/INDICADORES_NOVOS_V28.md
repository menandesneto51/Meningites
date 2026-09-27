# Indicadores novos V28 — Meningites CIEVS-MT

**Gerado em:** 27/09/2026 10:11

> Números estaduais. Recortes por regional e por ano estão nos CSVs `*_v28.csv`.

## Oportunidade de coleta liquórica

- Coleta ≤1 dia dos sintomas: **40,7%** (n=2.019/4.960)
- Coleta ≤2 dias dos sintomas: **55,4%** (n=2.750/4.960)
- Mediana sintomas→coleta: **2 dia(s)**
- P90 sintomas→coleta: **11 dia(s)**

## Tempo até quimioprofilaxia (DM e Hib)

- Quimio ≤2 dias entre elegíveis: **53,3%** (n=160/300)
- Quimio ≤2 dias entre casos com data: **85,1%** (n=160/188)
- Mediana notificação→quimio: **1 dia(s)**
- P90 notificação→quimio: **4 dia(s)**

## Cobertura de sorogrupo em DM confirmada (NT 154/2024)

- DM confirmada com sorogrupo preenchido: **30,5%** (n=85/279)

## Contatos por caso de DM

- Mediana de comunicantes por caso de DM: **7 contatos**
- DM com zero ou sem informação de comunicantes: **20,4%** (n=57/279)

## Subnotificação de mortalidade (SIM sem SINAN)

Fonte do linkage: `desfechos_mortalidade_sim_v23.csv`.

- Óbitos SIM sem desfecho no SINAN (sobre óbitos SIM): **31,2%** (n=20/64)
- Óbitos SIM sem desfecho no SINAN (sobre óbitos SINAN∪SIM): **4,8%** (n=20/418)

## Oportunidade de detecção (sintomas→notificação)

- Mediana: **3 dia(s)**
- P90: **13 dia(s)**
- Notificação ≤1 dia dos sintomas: **29,6%** (n=1.772/5.979)

## Casos sem denominador populacional

- Casos sem população de referência: **32,7%** (n=1.964/6.004)

## Completude dos campos essenciais

- Completude média dos campos essenciais: **77,7%**
  - SAO FELIX DO ARAGUAIA: 58,5% (pior campo: ClassificacaoMeningite = 0%)
  - PORTO ALEGRE DO NORTE: 69,2% (pior campo: SeNMeningiditisEspecificarSorogrupo = 1,6%)
  - COLIDER: 71,2% (pior campo: SeNMeningiditisEspecificarSorogrupo = 0%)
  - JUARA: 72,1% (pior campo: SeNMeningiditisEspecificarSorogrupo = 0%)
  - BARRA DO GARCAS: 72,1% (pior campo: SeNMeningiditisEspecificarSorogrupo = 0,8%)

## Letalidade padronizada por idade

- Estadual: bruta **11,6%** · padronizada **11,6%** (óbitos 406/3.514)
- Municípios com n≥10 e maior letalidade padronizada:
  - ALTO ARAGUAIA: padronizada 45,2% · bruta 41,7% · n=12
  - FELIZ NATAL: padronizada 40,0% · bruta 41,7% · n=12
  - LUCAS DO RIO VERDE: padronizada 32,4% · bruta 33,3% · n=21
  - POXOREO: padronizada 31,9% · bruta 25% · n=20
  - JUINA: padronizada 28,8% · bruta 23,5% · n=17

> Padronização direta por faixa etária do Informe; população-padrão = distribuição etária dos casos do estado no período. Faixas sem casos no município não entram na taxa: confira `peso_coberto_pct` antes de comparar municípios pequenos.

## Varredura espaço-temporal (DM, exploratória)

- Janelas com sinal: **7** em **2** município(s)
  - SINOP · semana de 2026-05-04: obs 2 vs esperado 0,2 (O/E 8)
  - VARZEA GRANDE · semana de 2025-11-24: obs 2 vs esperado 0,2 (O/E 8)

> Sinal exploratório; exige validação no território antes de qualquer ação.

## Como atualizar

```bat
py -3.13 28_indicadores_novos_v28.py
```