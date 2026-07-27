# Narrativa assistida — Boletim Meningites CIEVS-MT

**Gerado em:** 27/07/2026 15:31
**Modo:** recuperação normativa local (RAG) + síntese operacional

> Texto de apoio. Revisar e validar antes de divulgação oficial.

## Síntese executiva
## Parágrafo executivo (LLM)

O cenário epidemiológico das meningites em 2025 no estado de Mato Grosso registra 87 casos confirmados, resultando em uma incidência de 2,9 por 100 mil habitantes e uma letalidade de 18,4%, com 16 óbitos. A análise dos indicadores do Ministério da Saúde revela que, embora o percentual de confirmação laboratorial (44,4%) e a cobertura de quimioprofilaxia para Doença Meningocócica (54,7%) superem as referências nacionais, persistem desafios críticos. Destacam-se a baixa proporção de casos investigados em até 48h (93,6%) e encerrados em até 60 dias (83,6%), ambos abaixo das metas. A identificação de sorogrupo em DM (30,6%) e a notificação em até 24h do início dos sintomas (29,8%) são pontos de atenção que impactam a agilidade da resposta. Alertas operacionais, como 679 encerramentos fora do prazo e 292 em risco, somados a uma fila de 200 itens prioritários no CIEVS, reforçam a necessidade de otimização dos processos de vigilância e assistência, incluindo a melhoria da confirmação laboratorial. A validação humana é obrigatória.


**Pontos favoráveis**
- % confirmação laboratorial (PCR/cultura) — Informe MS em 44,4% (acima ou alinhado à referência nacional).
- % doença meningocócica com quimioprofilaxia ≤48h em 54,7% (acima ou alinhado à referência nacional).

**Pontos que exigem ação**
- % casos investigados em até 48h da notificação em 93,6% (vermelho vs referência Brasil).
- % casos encerrados em até 60 dias da notificação em 83,6% (vermelho vs referência Brasil).
- % DM com sorogrupo identificado em 30,6% (vermelho vs referência Brasil).
- % notificação em até 24h do início dos sintomas em 29,8% (vermelho vs referência Brasil).
- % meningite Hib/Hemófilo com quimioprofilaxia ≤48h em 38,1% (vermelho vs referência Brasil).

## Leitura normativa aplicada

Conforme Informe Meningites 2024 — CGVDI/DPNI/SVSA/MS: Indicadores de vigilância epidemiológica e laboratorial monitorados nacionalmente: (1) percentual de casos confirmados por critério laboratorial (RT-qPCR e cultura) — Brasil 2024: 36,1%; (2) percentual de casos investigados em até 48h da notificação — 97,8%; (3) percentual de casos encerrados em até 60 dias da notificação — 94,4%; (4) percentual de casos de DM com quimioprofilaxia de contatos em até 48h da notificaçã...

Sobre quimioprofilaxia (NT Conjunta nº 154/2024-DPNI/SVSA/MS (retifica e revoga a NT nº 97/2024-DPNI/SVSA/MS); Informe Meningites 2024): Objetivo: interromper transmissão por descolonização de nasofaringe e prevenir casos secundários. Realizar o mais breve possível nos contatos próximos de caso suspeito/confirmado de DM ou DIHib, idealmente nas primeiras 24h após início dos sintomas. O indicador nacional monitora quimio em DM em até 48h da notificação. Após 10 dias da exposição o valor é limitado/nulo na maioria dos casos secundários de DM; para DIHib...

## Prioridades sugeridas para a semana

1. Reduzir backlog de **encerramento >60 dias** e **investigação >48h** (indicadores MS).
2. Garantir **quimioprofilaxia oportuna** em DM/Hib e auditar quimio em etiologias não elegíveis.
3. Buscar **cultura/PCR** em bacterianas confirmadas sem critério laboratorial.
4. Manter vigilância de **aglomerados DM** (mesmo sorogrupo, ≤90 dias) segundo NT 154/2024.

## Contexto de dados usado

```
Indicadores MS (MT):
- % confirmação laboratorial (PCR/cultura) — Informe MS: 44,4% (ref BR 36,1; Verde)
- % casos investigados em até 48h da notificação: 93,6% (ref BR 97,8; Vermelho)
- % casos encerrados em até 60 dias da notificação: 83,6% (ref BR 94,4; Vermelho)
- % doença meningocócica com quimioprofilaxia ≤48h: 54,7% (ref BR 45,5; Verde)
- % DM com sorogrupo identificado: 30,6% (ref BR NA; Vermelho)
- % notificação em até 24h do início dos sintomas: 29,8% (ref BR NA; Vermelho)
- % meningite Hib/Hemófilo com quimioprofilaxia ≤48h: 38,1% (ref BR NA; Vermelho)
Epidemiologia 2025: confirmados=87; incidência=2,9/100 mil; letalidade=18,4%; óbitos=16
Principais alertas: Encerramento fora do prazo (Atenção) n=679; Confirmação laboratorial fraca (Atenção) n=591; Encerramento em risco/atrasado (Crítico) n=292; Investigação atrasada (Alto) n=210; Investigação fora do prazo (Atenção) n=168
Fila CIEVS: 200 itens prioritários.
```

---
*Gerado por 16_assistente_cievs_v23.py — CIEVS-MT*