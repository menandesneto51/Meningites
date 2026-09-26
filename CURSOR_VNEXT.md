# Cursor — Meningites VNext

## Regra permanente

Toda alteração feita localmente no Cursor deve respeitar a arquitetura e os gates documentados em:
- `docs/vnext/ARCHITECTURE.md`
- `docs/vnext/MODULE_MIGRATION.md`
- `docs/vnext/MUNICIPAL_ENGINE.md`
- `agents/README.md`

Não mover, apagar ou renomear scripts 00–35 enquanto `pipeline_meningites_v23_indicadores_ms.py` depender deles.

## Prompt operacional — próxima execução no Cursor

Você está trabalhando no repositório Meningites, branch `vnext/architecture-agents`.

Objetivo: validar localmente o Meningites VNext e preparar a integração do Motor de Situação Epidemiológica Municipal com os artefatos reais em `saida_meningites_v17`.

### Antes de editar
1. Leia os quatro documentos VNext listados acima.
2. Leia `src/meningites/domain/contracts.py`.
3. Leia `src/meningites/operational_queue/municipal_engine.py`, `legacy_aggregator.py` e `rules_catalog.py`.
4. Leia os módulos 20, 26, 32, 33, 34 e 35.
5. Não invente colunas, limiares, regras clínicas ou fontes.

### Validação
Execute:
```powershell
$env:PYTHONPATH="src"
python -m pytest -q tests/test_vnext_domain_contracts.py tests/test_vnext_municipal_engine.py tests/test_vnext_legacy_aggregator.py
```

Depois execute os testes de contrato já existentes do projeto.

### Integração local
Se `saida_meningites_v17` contiver os artefatos reais:
- confira o schema antes de mapear;
- registre colunas ausentes como erro de contrato, não como zero;
- nunca inferira município por nome quando houver ausência da chave territorial;
- não exporte PII;
- compare as contagens VNext com os arquivos-fonte;
- gere relatório de divergências antes de qualquer substituição do legado.

### Definition of Done
- todos os testes passam;
- nenhuma regressão nos contratos V28–V35;
- contagens municipais reconciliadas com os artefatos-fonte;
- sinais exibem fonte e regra;
- ausência de fonte não vira zero silenciosamente;
- nenhuma regra epidemiológica nova sem validação/fonte;
- alterações documentadas no PR com bloco Agent Review.

### Próximo alvo após validação
Criar um comando/entrypoint VNext que gere `situacao_municipal_vnext.csv` e `sinais_municipais_vnext.csv` a partir dos artefatos reais, preservando procedência.


## Incremento atual — publicação municipal VNext

O entrypoint já existe. No Cursor, após atualizar a branch, execute:

```powershell
$env:PYTHONPATH="src"
python pipelines/vnext_municipal.py --outdir saida_meningites_v17
```

Verifique obrigatoriamente:
- `saida_meningites_v17/situacao_municipal_vnext.csv`;
- `saida_meningites_v17/sinais_municipais_vnext.csv`;
- `saida_meningites_v17/divergencias_vnext.csv`;
- `saida_meningites_v17/procedencia_situacao_vnext.json`.

### Regra de validação local

1. Abra `divergencias_vnext.csv` primeiro.
2. Para qualquer `sem_chave_territorial`, identifique no módulo de origem se a chave municipal pode ser exportada legitimamente; não faça join por nome apenas para eliminar o alerta.
3. Compare manualmente pelo menos 5 municípios, incluindo Cuiabá e Várzea Grande quando existirem nas fontes, entre os arquivos legados e `situacao_municipal_vnext.csv`.
4. Confira que cada sinal possui `rule_id`, valor, limiar e fonte.
5. Não altere os arquivos legados durante essa validação.
6. Se houver divergência, corrija adapter/contrato; não ajuste a saída manualmente.

### Testes adicionais

```powershell
$env:PYTHONPATH="src"
python -m pytest -q tests/test_vnext_publisher.py
```

Somente após a reconciliação local, propor inclusão do entrypoint no pipeline principal.


## Validação adicional — módulos 26 e 34

Após executar o publisher VNext, valide também:

1. `score_risco_municipal_nt154_v25.csv` → colunas `v25_*` em `situacao_municipal_vnext.csv`.
2. `cipv_doses_agregadas_v34.csv` → `cipv_ano_mais_recente` e `cipv_doses_ano_mais_recente`.
3. Confirme que o VNext não converte automaticamente `v25_prioridade`, `v25_score_risco_nt154_v25` ou volume de doses em novos sinais.
4. Confirme que `cipv_doses_*` é tratado como número de doses, e nunca rotulado como cobertura populacional sem denominador apropriado.
5. Se códigos municipais 6/7 dígitos causarem duplicação territorial, registre a divergência e corrija a normalização somente após conferir o padrão real das fontes; não faça correção ad hoc por nome.

Execute ainda:

```powershell
$env:PYTHONPATH="src"
python -m pytest -q tests/test_vnext_descriptive_aggregator.py tests/test_vnext_publisher.py
```


## Validação adicional — indicadores municipais e cards VNext

Após executar o publisher, confirme a criação de:
- `indicadores_municipais_vnext.csv`;
- `cards_municipais_vnext_index.csv`;
- `cards_municipais_vnext_manifest.json`;
- diretório `cards_municipais_vnext/` com um Markdown por município presente na situação consolidada.

### Regras obrigatórias
1. O denominador municipal deve vir do artefato do módulo 12, nunca ser inventado.
2. Quando o numerador não estiver exportado pelo módulo 12 municipal, ele deve permanecer vazio com `numerador_status=nao_exportado_pelo_modulo_12_municipal`.
3. Não reconstruir numerador por `percentual × denominador`.
4. A referência e a vigência devem ser herdadas de `indicadores_ms_operacionais_base_v23.csv` ou, na ausência, do artefato canônico equivalente.
5. Conferir manualmente ao menos 5 cards contra os CSV-fonte.
6. O card deve diferenciar claramente: fila/sinal acionável, contexto V25, doses CIPV e indicador operacional.
7. Doses CIPV nunca devem aparecer como cobertura populacional sem denominador adequado.
8. Antes de incorporar card em painel/PDF, corrigir qualquer divergência de chave municipal.

Execute:
```powershell
$env:PYTHONPATH="src"
python -m pytest -q tests/test_vnext_municipal_cards.py tests/test_vnext_publisher.py
python pipelines/vnext_municipal.py --outdir saida_meningites_v17
```


## Validação adicional — visão executiva e agente epidemiológico

Após executar o publisher, confirme a criação de:
- `resumo_executivo_regional_vnext.csv`;
- `resumo_executivo_estadual_vnext.csv`;
- `agente_epidemiologico_contexto_vnext.json`.

### Regras obrigatórias
1. A regional deve ser derivada do mapeamento municipal presente nos indicadores do módulo 12; ausência de regional deve aparecer como `Sem regional`, nunca ser adivinhada.
2. A visão executiva só agrega sinais já existentes; não cria novo limiar nem reclassifica automaticamente municípios.
3. O JSON do agente deve preservar os guardrails: sem criação de regra clínica, sem inferência de numerador, sem interpretar doses como cobertura e com obrigação de distinguir fato de interpretação.
4. Verifique que cada sinal municipal do contexto do agente mantém `rule_id` e fonte quando existirem na saída publicada.
5. Compare os totais estadual e regional com `sinais_municipais_vnext.csv` e `situacao_municipal_vnext.csv`.
6. Não permitir que o agente substitua decisão sanitária humana nem emita conduta clínica sem referência oficial validada.

Execute:
```powershell
$env:PYTHONPATH="src"
python -m pytest -q tests/test_vnext_executive_agent.py tests/test_vnext_publisher.py
python pipelines/vnext_municipal.py --outdir saida_meningites_v17
```

### Uso no Cursor
Ao pedir interpretação ao Cursor/LLM, use `agente_epidemiologico_contexto_vnext.json` como contexto estruturado primário e o corpus `docs_ms/` para fundamentação normativa. Não peça ao modelo para recalcular os indicadores a partir de arquivos brutos se o publisher já tiver produzido o fato canônico.


## Validação adicional — agente epidemiológico operacional

Cada execução do publisher deve gerar também:
- `agente_briefing_estadual_vnext.md`;
- `agente_briefings_regionais_vnext.json`;
- `agente_lacunas_dados_vnext.json`.

### Regras obrigatórias
1. O briefing estadual deve reproduzir apenas totais presentes em `resumo_executivo_estadual_vnext.csv`.
2. O briefing regional deve reproduzir apenas a agregação publicada em `resumo_executivo_regional_vnext.csv`.
3. A explicação municipal deve preservar `rule_id`, prioridade, valor e fonte dos sinais.
4. O agente deve falhar se `may_create_clinical_rules` não estiver explicitamente como `false`.
5. Ausência no contexto deve ser descrita como ausência de informação, nunca como ausência de risco/evento.
6. O agente determinístico é o baseline auditável. Qualquer enriquecimento por LLM/RAG deve manter esses fatos intactos e apenas adicionar interpretação fundamentada.
7. Não permitir que o LLM altere contagens, regras ou prioridades publicadas pelo VNext.

Execute:
```powershell
$env:PYTHONPATH="src"
python -m pytest -q tests/test_vnext_operational_agent.py tests/test_vnext_publisher.py
python pipelines/vnext_municipal.py --outdir saida_meningites_v17
```

### Próximo alvo no Cursor
Preparar um adapter entre o agente VNext e a RAG existente do módulo 16/27. O adapter deve enviar ao LLM apenas:
- pergunta do usuário;
- fatos canônicos VNext relevantes;
- trechos normativos recuperados do corpus vigente;
- guardrails do agente.

O LLM não deve receber autoridade para recalcular indicadores nem substituir os artefatos publicados.


## Validação adicional — adapter RAG VNext

Cada execução do publisher deve gerar também:
- `agente_rag_pacotes_vnext.json`;
- `agente_rag_prompts_vnext.json`.

### Regras obrigatórias
1. A fonte normativa primária do adapter é `assistente_kb_docs_ms_v27.csv`, gerada pelo módulo 27 a partir de `docs_ms/`.
2. Por padrão, documentos marcados como revogados/não vigentes não entram nos pacotes normativos.
3. O pacote deve manter seções separadas para `canonical_facts`, `normative_evidence`, `guardrails` e `response_contract`.
4. O prompt deve proibir explicitamente recalcular indicadores, alterar prioridades e criar regras clínicas.
5. Se não houver evidência normativa suficiente, a futura resposta LLM deve declarar insuficiência em vez de preencher lacunas por conhecimento não rastreado.
6. O adapter não chama LLM durante a publicação; ele apenas prepara um contrato auditável.
7. Nenhum texto gerado por LLM deve sobrescrever os CSV/JSON canônicos do VNext.

Execute:
```powershell
$env:PYTHONPATH="src"
python -m pytest -q tests/test_vnext_rag_adapter.py tests/test_vnext_publisher.py
python pipelines/vnext_municipal.py --outdir saida_meningites_v17
```

### Próximo alvo no Cursor
Implementar um cliente LLM opcional sobre `agente_rag_pacotes_vnext.json`, reutilizando credenciais já suportadas pelo projeto, mas com validação pós-resposta que rejeite alterações de fatos canônicos e respostas sem fundamentação normativa quando a pergunta exigir norma.


## Validação adicional — cliente LLM opcional e pós-validação

O publisher deve gerar `agente_llm_validacao_vnext.json` como template de controle, mas **não deve chamar LLM automaticamente**.

### Regras obrigatórias
1. O cliente LLM reutiliza apenas credenciais locais já suportadas: `LLM_API_KEY`, `GEMINI_API_KEY`, `MENINGITES_OPENAI_API_KEY` ou `OPENAI_API_KEY`.
2. Ausência de credencial deve resultar em `status=unavailable`, nunca falha do pipeline principal.
3. Toda resposta LLM deve passar por `validate_llm_response` antes de qualquer uso.
4. O validador rejeita:
   - números não rastreados em fatos canônicos ou evidência normativa;
   - ausência das seções FATOS, INTERPRETAÇÃO, RECOMENDAÇÕES e LIMITAÇÕES;
   - ausência de fonte normativa quando houver evidência normativa;
   - conduta clínica não autorizada.
5. Mesmo respostas aceitas ficam com `requires_human_review=true`.
6. Respostas rejeitadas nunca devem substituir briefing determinístico, CSVs ou JSONs canônicos.
7. O pipeline VNext não deve fazer chamadas externas de IA por padrão.

Execute:
```powershell
$env:PYTHONPATH="src"
python -m pytest -q tests/test_vnext_llm_guardrails.py tests/test_vnext_publisher.py
python pipelines/vnext_municipal.py --outdir saida_meningites_v17
```

### Teste manual opcional no Cursor
Somente após os testes acima e com credencial configurada, carregar um pacote de `agente_rag_pacotes_vnext.json`, renderizar o prompt correspondente e executar `run_validated_llm`. Revisar `issues` e confirmar manualmente a resposta antes de qualquer uso operacional.
