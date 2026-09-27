# Meningites VNext — Arquitetura de Referência

Status: ADR de transição arquitetural
Data: 2026-09-26
Estratégia: migração incremental (strangler), sem ruptura do pipeline operacional.

## Objetivos

1. Transformar o conjunto evolutivo de scripts em uma plataforma modular de inteligência epidemiológica.
2. Preservar resultados, contratos, rastreabilidade, regras epidemiológicas e compatibilidade durante a migração.
3. Separar domínio, ingestão, qualidade, linkage, análise, inteligência operacional, apresentação e conhecimento normativo.
4. Tornar toda interpretação operacional explicável: dado -> regra/limiar -> fonte normativa -> ação sugerida.
5. Preparar execução local e implantação institucional, sem segredos no código.

## Estrutura-alvo

```text
app/
  dashboard/
  api/
  assistant/
src/meningites/
  domain/
    surveillance/
    laboratory/
    vaccination/
    contacts/
    outcomes/
  ingestion/
    sinan/
    gal/
    sim/
    sih/
    sipni/
    cnes/
    sinasc/
    redcap/
  quality/
  linkage/
  analytics/
  epidemiology/
  spatial/
  forecasting/
  alerts/
  operational_queue/
  reporting/
  provenance/
knowledge/
  ms/
  ses_mt/
  rag/
agents/
pipelines/
contracts/
tests/
archive/
```

## Modelo canônico de caso

- case
- case_notification
- case_classification
- case_clinical
- case_lab
- case_contacts
- case_prophylaxis
- case_vaccination
- case_hospitalization
- case_outcome
- case_surveillance_action
- case_quality_issue

Cada entidade deve carregar chaves técnicas, fonte, data de extração/competência e atributos necessários à auditoria.

## Regras de migração

- Nenhum script 00–35 será apagado ou movido enquanto for chamado pelo orquestrador vigente.
- Novos componentes entram primeiro em `src/meningites` e recebem adaptadores para os artefatos legados.
- Um módulo só substitui o legado após equivalência de contrato e testes.
- Artefatos públicos permanecem sem PII; pseudonimização continua obrigatória.
- Regras clínicas/epidemiológicas exigem fonte oficial e vigência explícita.
- Modelos preditivos não substituem definição de caso, investigação ou decisão sanitária.
- Falhas de fontes críticas devem ser visíveis e, nas rotinas definidas como críticas, fail-closed.
- Toda saída operacional deve registrar procedência e horário de geração.

## Motor de Situação Epidemiológica Municipal

Componente prioritário do VNext. Produzirá, por município e período:

- sinais epidemiológicos;
- pendências de investigação;
- pendências laboratoriais/GAL;
- situação de contatos e quimioprofilaxia;
- reconciliação SINAN/SIM/SIH;
- qualidade e oportunidade dos dados;
- comparação com baseline histórico;
- regra que disparou cada sinal;
- fonte normativa aplicável e vigência;
- ação sugerida, sem inventar conduta clínica.

O motor deve alimentar fila CIEVS, resumo regional, card municipal e briefing executivo.

## Critério de saída da transição

A arquitetura VNext torna-se canônica quando os contratos automatizados demonstrarem equivalência ou melhoria deliberadamente documentada para os produtos operacionais vigentes.
