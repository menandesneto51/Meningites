# Inventário de Migração — módulos 00–35

Classificação inicial para orientar a consolidação. "Incorporar" significa migrar lógica útil para o domínio VNext mantendo adaptador legado até equivalência.

| Módulo | Função dominante | Destino VNext | Decisão |
|---|---|---|---|
| 00 | base única | ingestion + domain | incorporar |
| 01 | KPIs semanais | epidemiology | incorporar |
| 02 | estatística/OR | analytics | incorporar |
| 02b | OR classificação/desfecho | analytics | incorporar |
| 02c | OR clínico/sócio/comorbidades | analytics | incorporar |
| 03 | surtos/canal endêmico | epidemiology/alerts | incorporar |
| 04 | nowcast/forecast | forecasting | incorporar |
| 04b | nowcast desfechos | forecasting | incorporar |
| 05 | espacial/Moran/distância lab | spatial | incorporar |
| 06 | clima | analytics/environmental | incorporar |
| 07 | laboratório/qualidade | laboratory + quality | incorporar |
| 08 | vacina/etiologia | vaccination + analytics | incorporar |
| 09 | relatório técnico | reporting | incorporar |
| 10 | comorbidades | analytics | incorporar |
| 11 | score qualidade | quality | incorporar |
| 12 | indicadores MS operacionais | epidemiology/operational_queue | prioridade canônica |
| 13 | alertas inteligentes | alerts | prioridade canônica |
| 14 | painel epidemiológico | app/dashboard | desacoplar da regra |
| 15 | boletim semanal | reporting | incorporar |
| 16 | assistente CIEVS | app/assistant + knowledge/rag | incorporar |
| 17 | linkage GAL/LACEN/SIM | linkage | prioridade canônica |
| 18 | arquivamento legado | archive/tooling | manter até fim da migração |
| 19 | DW descobrir/extrair | ingestion | prioridade canônica |
| 20 | enriquecimento DW/fila CIEVS | operational_queue | prioridade canônica |
| 21 | sazonalidade | epidemiology | incorporar |
| 22 | nowcast/forecast refinado | forecasting | preferir sobre versões anteriores após contrato |
| 23 | alertas personalizados IA | alerts/assistant | incorporar com guardrails |
| 24 | nowcast operacional gestão | forecasting/operational_queue | prioridade canônica |
| 25 | exportação geo cloud | spatial/publishing | incorporar |
| 26 | indicadores ops avançados | epidemiology/operational_queue | prioridade canônica |
| 27 | ingestão docs MS/RAG | knowledge/rag | prioridade canônica |
| 28 | indicadores novos | epidemiology | incorporar |
| 29 | procedência artefatos | provenance | prioridade canônica |
| 30 | CNES/SINASC | ingestion/cnes + ingestion/sinasc | prioridade canônica |
| 31 | população IBGE/RIPSA | ingestion/population | prioridade canônica |
| 32 | GAL detalhado | ingestion/gal + laboratory | prioridade canônica |
| 33 | SIH/subnotificação | ingestion/sih + linkage | prioridade canônica |
| 34 | CIPV/cobertura vacinal | ingestion/sipni + vaccination | prioridade canônica |
| 35 | RedCap/fila CIEVS | ingestion/redcap + operational_queue | prioridade canônica |

## Ordem de consolidação

1. Contratos e procedência.
2. Ingestão institucional e modelo canônico.
3. Linkage/reconciliação.
4. Indicadores e fila operacional.
5. Alertas e motor municipal.
6. Forecast/espacial/analytics.
7. Relatórios, dashboard e assistente.
8. Arquivamento do legado somente após testes de equivalência.

## Regra anti-regressão

Nenhum módulo é classificado como "arquivar" apenas por possuir número de versão antigo. A decisão depende de dependências reais, cobertura funcional, contrato de saída, uso no pipeline e equivalência comprovada.
