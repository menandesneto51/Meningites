# Indicadores novos V28 — Meningites CIEVS-MT

**Gerado em:** 29/07/2026 12:37

> Números estaduais. Recortes por regional e por ano estão nos CSVs `*_v28.csv`.

## Oportunidade de coleta liquórica

- Coleta ≤1 dia dos sintomas: **40,8%** (n=2.008/4.918)
- Coleta ≤2 dias dos sintomas: **55,7%** (n=2.737/4.918)
- Mediana sintomas→coleta: **2 dia(s)**
- P90 sintomas→coleta: **11 dia(s)**

## Tempo até quimioprofilaxia (DM e Hib)

- Quimio ≤2 dias entre elegíveis: **53,5%** (n=160/299)
- Quimio ≤2 dias entre casos com data: **85,1%** (n=160/188)
- Mediana notificação→quimio: **1 dia(s)**
- P90 notificação→quimio: **4 dia(s)**

## Cobertura de sorogrupo em DM confirmada (NT 154/2024)

- DM confirmada com sorogrupo preenchido: **30,6%** (n=85/278)

## Contatos por caso de DM

- Mediana de comunicantes por caso de DM: **7 contatos**
- DM com zero ou sem informação de comunicantes: **20,1%** (n=56/278)

## Subnotificação de mortalidade (SIM sem SINAN)

Fonte do linkage: `desfechos_mortalidade_sim_v23.csv`.

- Óbitos SIM sem desfecho no SINAN (sobre óbitos SIM): **31,2%** (n=20/64)
- Óbitos SIM sem desfecho no SINAN (sobre óbitos SINAN∪SIM): **4,8%** (n=20/415)

## Oportunidade de detecção (sintomas→notificação)

- Mediana: **3 dia(s)**
- P90: **13 dia(s)**
- Notificação ≤1 dia dos sintomas: **29,8%** (n=1.762/5.919)

## Casos sem denominador populacional

- Casos sem população de referência: **80,0%** (n=4.755/5.944)

## Completude dos campos essenciais

- Completude média dos campos essenciais: **77,7%**
  - SAO FELIX DO ARAGUAIA: 58,5% (pior campo: ClassificacaoMeningite = 0%)
  - PORTO ALEGRE DO NORTE: 68,4% (pior campo: SeNMeningiditisEspecificarSorogrupo = 1,6%)
  - COLIDER: 71,3% (pior campo: SeNMeningiditisEspecificarSorogrupo = 0%)
  - JUARA: 71,5% (pior campo: SeNMeningiditisEspecificarSorogrupo = 0%)
  - BARRA DO GARCAS: 72,1% (pior campo: SeNMeningiditisEspecificarSorogrupo = 0,8%)

## Letalidade padronizada por idade

- Estadual: bruta **11,5%** · padronizada **11,5%** (óbitos 403/3.495)
- Municípios com n≥10 e maior letalidade padronizada:
  - ALTO ARAGUAIA: padronizada 45,2% · bruta 41,7% · n=12
  - FELIZ NATAL: padronizada 40,0% · bruta 41,7% · n=12
  - LUCAS DO RIO VERDE: padronizada 32,4% · bruta 33,3% · n=21
  - POXOREO: padronizada 31,9% · bruta 25% · n=20
  - SAPEZAL: padronizada 31,3% · bruta 28,6% · n=28

> Padronização direta por faixa etária do Informe; população-padrão = distribuição etária dos casos do estado no período. Faixas sem casos no município não entram na taxa: confira `peso_coberto_pct` antes de comparar municípios pequenos.

## Varredura espaço-temporal (DM, exploratória)

- Janelas com sinal: **4** em **1** município(s)
  - SINOP · semana de 2026-05-04: obs 2 vs esperado 0,2 (O/E 8)

> Sinal exploratório; exige validação no território antes de qualquer ação.

## Como atualizar

```bat
py -3.13 28_indicadores_novos_v28.py
```