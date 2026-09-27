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


## Validação adicional — interface de consulta do agente

Novo entrypoint:
```powershell
$env:PYTHONPATH="src"
python pipelines/vnext_agent_query.py "Qual a situação de Cuiabá?" --scope "Cuiabá"
```

Exemplos:
```powershell
python pipelines/vnext_agent_query.py "Quais os principais sinais do estado?" --scope "Mato Grosso"
python pipelines/vnext_agent_query.py "Quais as pendências da regional?" --scope "Baixada Cuiabana"
python pipelines/vnext_agent_query.py "Explique os sinais deste município" --scope "5103403"
python pipelines/vnext_agent_query.py "Quais lacunas de dados existem?" --mode gaps
```

Uso opcional de LLM validado:
```powershell
python pipelines/vnext_agent_query.py "O que a norma vigente orienta sobre esta pendência?" --scope "Cuiabá" --llm
```

### Regras obrigatórias
1. Sem `--llm`, a consulta deve funcionar integralmente em modo determinístico/RAG local.
2. `--llm` é opt-in e sempre passa pelo validador pós-resposta.
3. O modo `auto` deve resolver estado, regional ou município a partir do contexto publicado.
4. Município pode ser consultado por código ou nome exato presente no contexto.
5. Escopo não encontrado não pode ser tratado como ausência de evento; retornar contexto ausente.
6. Resultado sempre mantém `human_validation_required=true`.
7. A interface não altera qualquer artefato canônico; `--save` grava apenas o resultado da consulta.

Execute:
```powershell
$env:PYTHONPATH="src"
python -m pytest -q tests/test_vnext_agent_query.py tests/test_vnext_llm_guardrails.py
```

### Próximo alvo no Cursor
Após validar a CLI com dados reais, criar uma camada HTTP fina sobre `query_agent()` apenas se houver necessidade operacional, mantendo a função Python como contrato principal para evitar acoplamento de framework.


## Validação adicional — chave territorial IBGE-6 e API HTTP opcional

### Chave territorial
O contrato VNext foi alinhado ao legado institucional: a chave municipal interna é **IBGE-6**.

Regras:
1. Entradas IBGE-7 são aceitas e normalizadas para os seis primeiros dígitos.
2. Fontes com `510340` e `5103403` devem convergir para o mesmo município.
3. Nunca inferir código por nome.
4. Conferir `docs/vnext/TERRITORY_KEY.md`.
5. Validar especialmente Cuiabá e Várzea Grande contra os arquivos reais, verificando se não há duplicatas 6×7.

Execute:
```powershell
$env:PYTHONPATH="src"
python -m pytest -q tests/test_vnext_legacy_aggregator.py tests/test_vnext_agent_query.py
```

### API HTTP opcional
A API é apenas um adapter de transporte sobre `query_agent()`.

Instalação opcional:
```powershell
pip install -r requirements-api.txt
```

Execução local:
```powershell
$env:PYTHONPATH="src"
python pipelines/vnext_agent_api.py --outdir saida_meningites_v17 --host 127.0.0.1 --port 8765
```

Endpoints:
- `GET /health`
- `POST /v1/query`

Payload de exemplo:
```json
{
  "question": "Qual a situação de Cuiabá?",
  "scope": "Cuiabá",
  "mode": "auto",
  "use_llm": false
}
```

Regras obrigatórias:
1. A API não deve conter lógica epidemiológica própria.
2. A API não deve modificar arquivos canônicos.
3. LLM permanece desligado por padrão.
4. Contexto não publicado retorna indisponibilidade; não inventar resposta.
5. Para exposição fora de localhost, exigir autenticação, TLS e revisão Security/LGPD antes de qualquer implantação institucional.
6. Não publicar esta API diretamente na internet durante a fase atual.

Execute também:
```powershell
python -m pytest -q tests/test_vnext_agent_http.py
```

### Próximo alvo no Cursor
Após validar dados reais e a API local, integrar o endpoint ao painel apenas em ambiente de desenvolvimento e implementar autenticação/autorização antes de qualquer exposição em rede institucional.


## Validação adicional — integração Streamlit por feature flag

A aba `23 Agente VNext (dev)` está integrada ao dashboard, mas deve permanecer **desligada por padrão**.

### Ativação local
```powershell
$env:PYTHONPATH="src"
$env:MENINGITES_VNEXT_AGENT_UI="true"
streamlit run streamlit_app.py
```

Sem a variável acima, o dashboard deve manter exatamente as 22 abas existentes e não carregar o componente VNext.

### Regras obrigatórias
1. `MENINGITES_VNEXT_AGENT_UI` deve permanecer ausente/false no ambiente atual de produção.
2. A aba VNext usa `query_agent()`; não duplicar lógica epidemiológica dentro do Streamlit.
3. LLM permanece desmarcado por padrão na interface.
4. Se o contexto VNext não existir, exibir aviso e não tentar inferir resposta.
5. Evidência normativa deve ser exibida separadamente da resposta determinística.
6. Resposta LLM rejeitada pelo validador deve aparecer como rejeitada e não ser usada como resposta operacional.
7. A interface deve reiterar revisão humana obrigatória.
8. Não expor a API HTTP ou a aba VNext externamente antes da validação local com dados reais.

### Cenários de validação manual
- Mato Grosso: pergunta estadual;
- Baixada Cuiabana: pergunta regional;
- Cuiabá por nome;
- Cuiabá por IBGE-7 `5103403` e IBGE-6 `510340`;
- Várzea Grande por nome/código;
- escopo inexistente;
- corpus normativo ausente;
- LLM sem credencial;
- resposta LLM rejeitada (teste controlado).

Execute:
```powershell
python -m pytest -q tests/test_vnext_feature_flags.py tests/test_vnext_agent_query.py tests/test_vnext_agent_http.py
```

### Próximo alvo no Cursor
Executar o dashboard local com a feature flag ativa, conferir visualmente a aba, revisar logs e divergências e só então propor integração permanente. Não ativar a flag em Streamlit Cloud/produção nesta fase.


## Validação adicional — numeradores municipais exatos do módulo 12

O módulo 12 passa a exportar, de forma aditiva e retrocompatível, os numeradores/denominadores municipais reais usados nos quatro indicadores principais:
- `bact_lab_informe_pcr_cultura / bact_confirmadas`;
- `investigados_48h / total_notificacoes`;
- `encerrados_60d / total_notificacoes`;
- `dm_quimio_48h / dm_casos`.

Também exporta no artefato municipal:
- `referencia_ano`;
- `referencia_periodo`;
- `referencia_fonte`;
- `referencia_vigencia_desde`.

### Regras obrigatórias
1. Não reconstruir numerador por percentual × denominador.
2. Em artefatos antigos, numerador/denominador ausente deve permanecer vazio com status explícito.
3. Em artefatos novos, `numerador_status=ok` e `denominador_status=ok` quando os campos estiverem presentes.
4. Conferir pelo menos 5 municípios contra o recálculo direto do módulo 12, incluindo Cuiabá e Várzea Grande quando presentes.
5. Verificar que os cards municipais mostram numerador e denominador reais.
6. Confirmar que a mudança é apenas aditiva: nenhuma coluna legada foi removida ou renomeada.

Execute:
```powershell
$env:PYTHONPATH="src"
python 12_indicadores_ms_operacionais_v23.py
python -m pytest -q tests/test_vnext_municipal_cards.py tests/test_vnext_publisher.py
python pipelines/vnext_municipal.py --outdir saida_meningites_v17
```

Depois compare `indicadores_ms_operacionais_municipio_v23.csv` com `indicadores_municipais_vnext.csv` e registre divergências, se houver.


## Gate formal — reconciliação automatizada VNext

Novo comando:

```powershell
$env:PYTHONPATH="src"
python pipelines/vnext_validate.py --outdir saida_meningites_v17 --strict
```

Saídas:
- `validacao_vnext.json`;
- `VALIDACAO_VNEXT.md`.

### Significado
- `PASS`: reconciliação técnica sem falhas bloqueantes; revisão humana ainda obrigatória.
- `ATTENTION`: existem ausências ou condições que precisam ser revistas antes de ativação permanente.
- `FAIL`: não integrar ao pipeline principal nem ativar a feature flag em produção.

### Checks atuais
1. Chave territorial IBGE-6 válida nas saídas VNext.
2. Ausência de duplicação territorial 6×7 nas saídas consolidadas.
3. Reconciliação módulo 12 × `indicadores_municipais_vnext.csv` para valor, numerador e denominador.
4. Sinais com `rule_id`, fonte e chave territorial válida.
5. `divergencias_vnext.csv` sem `erro_leitura`, `sem_chave_territorial` ou arquivo vazio.

### Sequência obrigatória no Cursor
```powershell
$env:PYTHONPATH="src"
python 12_indicadores_ms_operacionais_v23.py
python pipelines/vnext_municipal.py --outdir saida_meningites_v17
python pipelines/vnext_validate.py --outdir saida_meningites_v17 --strict
```

Somente se o status for `PASS`:
1. ativar `MENINGITES_VNEXT_AGENT_UI=true` localmente;
2. testar dashboard e consultas;
3. revisar visualmente os cards;
4. registrar o resultado no PR.

Se houver `FAIL`, corrigir o adapter/contrato/fonte e repetir o ciclo. Não editar CSV de saída manualmente para “fazer passar”.

### Próximo alvo
Depois de obter `PASS` com dados reais, incorporar o validador como gate do pipeline principal e criar um resumo de saúde operacional do VNext no dashboard de desenvolvimento.


## Validação adicional — saúde operacional visível

O resultado de `validacao_vnext.json` agora é consumido por:
- aba `23 Agente VNext (dev)` no Streamlit;
- endpoint `GET /health` da API local.

### Comportamento esperado
- `PASS`: interface mostra gate aprovado e `blocking=false`;
- `ATTENTION`: interface mostra aviso e mantém bloqueio para ativação permanente;
- `FAIL`: interface mostra erro e mantém bloqueio;
- sem relatório: `not_validated` e bloqueio;
- JSON inválido: `invalid_report` e bloqueio.

### Regras obrigatórias
1. Saúde operacional deve ser lida de `validacao_vnext.json`; não recalcular checks na UI/API.
2. UI/API nunca devem promover `ATTENTION` ou `FAIL` como estado saudável.
3. O endpoint `/health` deve retornar `status=degraded` quando o gate não estiver em PASS.
4. A aba deve mostrar primeiro falhas, depois atenções, depois passes.
5. A existência do contexto do agente não substitui o gate de validação.
6. Não ativar a feature flag em produção se `blocking=true`.

Execute:
```powershell
$env:PYTHONPATH="src"
python -m pytest -q tests/test_vnext_reconciliation.py tests/test_vnext_validation_health.py tests/test_vnext_agent_http.py
python pipelines/vnext_validate.py --outdir saida_meningites_v17 --strict
```

### Próximo alvo no Cursor
Quando houver PASS real, salvar uma evidência do gate (JSON/Markdown) junto do PR e executar a validação visual da aba VNext. Só depois disso avaliar a incorporação do validador ao pipeline principal.


## Evidência formal de validação

Após obter `PASS` real:

```powershell
$env:PYTHONPATH="src"
python pipelines/vnext_capture_evidence.py --outdir saida_meningites_v17 --commit <SHA_DO_COMMIT>
```

Saídas:
- `evidencia_validacao_vnext.json`;
- `EVIDENCIA_VALIDACAO_VNEXT.md`.

A captura falha se:
- `validacao_vnext.json` não existir;
- o status não for `PASS`;
- qualquer artefato canônico obrigatório estiver ausente.

A evidência registra:
- commit validado;
- data/hora;
- status do gate;
- SHA-256 e tamanho dos artefatos canônicos;
- obrigação de revisão humana.

### Regra operacional
O PR só deve ser considerado tecnicamente pronto para merge quando houver:
1. CI verde;
2. gate real em `PASS`;
3. evidência de validação capturada;
4. revisão visual local da aba VNext;
5. Agent Review final registrado no PR.

Não gerar evidência manualmente nem editar hashes/relatório.


## Preflight único — comando preferencial no Cursor

A validação local completa passa a ter um único entrypoint:

```powershell
$env:PYTHONPATH="src"
python pipelines/vnext_preflight.py --repo-root . --outdir saida_meningites_v17 --commit <SHA_DO_COMMIT>
```

O preflight executa:
1. módulo 12;
2. publisher VNext;
3. gate de reconciliação;
4. captura de evidência somente se o gate estiver em `PASS`.

Saída adicional:
- `saida_meningites_v17/preflight_vnext.json`.

### Comportamento
- falha no módulo 12 → interrompe;
- `FAIL` no gate → interrompe e não captura evidência;
- `ATTENTION` → não captura evidência;
- `PASS` → gera evidência com hashes SHA-256;
- sempre mantém `human_review_required=true`.

### Uso quando o módulo 12 já tiver sido executado
```powershell
python pipelines/vnext_preflight.py --repo-root . --outdir saida_meningites_v17 --commit <SHA> --skip-module12
```

### Regra
Este passa a ser o comando preferencial de validação local. Os comandos separados continuam disponíveis para diagnóstico, mas não devem substituir o preflight no registro final do PR.


## Gate final de prontidão para merge/ativação

Depois do preflight em PASS e da revisão visual:

1. registrar a revisão visual humana:
```powershell
python pipelines/vnext_record_visual_review.py --outdir saida_meningites_v17 --reviewer "Menandes" --approved --notes "Dashboard e cards revisados localmente."
```

2. avaliar prontidão:
```powershell
python pipelines/vnext_readiness.py --outdir saida_meningites_v17 --strict
```

Saídas:
- `prontidao_vnext.json`;
- `PRONTIDAO_VNEXT.md`.

O status só será `READY` quando existirem simultaneamente:
- `validacao_vnext.json` em PASS;
- `evidencia_validacao_vnext.json` válida;
- `preflight_vnext.json` em PASS;
- `REVISAO_VISUAL_VNEXT.json` aprovada e com revisor identificado.

### Regra
O estado `READY` não realiza merge nem ativação automaticamente. Ele apenas comprova que os requisitos técnicos e a revisão visual foram satisfeitos. A decisão de merge permanece humana e explícita.


## Relatório executivo de release readiness

Depois que o gate `vnext_readiness.py --strict` retornar READY, gere o relatório consolidado:

```powershell
python pipelines/vnext_release_readiness.py `
  --outdir saida_meningites_v17 `
  --ci-status success `
  --ci-run 95 `
  --commit <SHA_DO_COMMIT> `
  --strict
```

Saídas:
- `release_readiness_vnext.json`;
- `RELEASE_READINESS_VNEXT.md`.

O relatório reúne:
- estado do CI;
- PASS local;
- preflight;
- evidência hashada;
- revisão visual;
- prontidão técnica;
- bloqueios remanescentes.

### Regra
`ready_for_merge_review=true` significa apenas que o PR pode entrar em revisão final para merge. Não realiza merge e não autoriza ativação automática em produção.


## Contrato estruturado de resposta LLM V2

O agente passa a preferir respostas JSON estritas com `schema_version=llm-response-vnext-2`.

Estrutura esperada:
- `facts[]`: `text` + `fact_refs`;
- `interpretations[]`: `text` + `fact_refs`;
- `recommendations[]`: `text` + `fact_refs` + `normative_evidence_ids`;
- `limitations[]`;
- `human_validation_required=true`.

### Regras
1. Cada `fact_ref` deve apontar para um caminho existente dentro de `canonical_facts`.
2. Cada `normative_evidence_id` deve existir no pacote RAG vigente.
3. Se houver evidência normativa disponível, recomendações sem `normative_evidence_ids` são rejeitadas.
4. Referência inexistente invalida a resposta.
5. O runner mantém o formato legado apenas como fallback compatível.
6. O formato estruturado não usa o detector numérico como fonte primária de validação; a rastreabilidade passa a ocorrer pelas referências explícitas.
7. Mesmo respostas V2 aceitas continuam com revisão humana obrigatória.

Execute:
```powershell
$env:PYTHONPATH="src"
python -m pytest -q tests/test_vnext_structured_llm.py tests/test_vnext_llm_guardrails.py
```


## Hardening adicional — vigência fail-closed e data quality no agente

### Vigência normativa
O RAG não deve mais tratar ausência de `vigente` como documento vigente.
- `vigente=true/sim/yes/1` → elegível por padrão;
- `vigente=false` → excluído de `current_only`;
- campo ausente, `null` ou `NaN` → considerado **não vigente/indeterminado** e excluído do retrieval padrão.

### Qualidade de dados no contexto do agente
`agente_epidemiologico_contexto_vnext.json` passa a incluir `data_quality` com:
- `artifact_status_rows`;
- `blocking_divergences_n`;
- `missing_artifacts_n`;
- `has_blocking_divergences`.

O RAG inclui `data_quality` dentro de `canonical_facts`, e `data_gaps()` deve listar divergências de artefatos como lacunas explícitas.

### Regras
1. Documento sem vigência explícita não pode fundamentar recomendação normativa corrente.
2. Ausência/erro/chave territorial ausente/vazio deve ser visível para o agente.
3. O agente não pode interpretar ausência de fonte como ausência de evento.
4. Divergência bloqueante deve aparecer no contexto antes de qualquer enriquecimento LLM.

Execute:
```powershell
$env:PYTHONPATH="src"
python -m pytest -q tests/test_vnext_rag_adapter.py tests/test_vnext_operational_agent.py tests/test_vnext_publisher.py
```


## Gate de qualidade de dados no readiness

O estado `READY` agora exige também que `agente_epidemiologico_contexto_vnext.json` informe:
- `has_blocking_divergences=false`;
- `blocking_divergences_n=0`.

### Regra
Mesmo com CI verde, preflight em PASS, evidência capturada e revisão visual aprovada, o VNext permanece bloqueado se houver divergência crítica de dados.

Exemplos bloqueantes:
- `erro_leitura`;
- `sem_chave_territorial`;
- arquivo `vazio` quando esperado como fonte operacional.

Execute:
```powershell
$env:PYTHONPATH="src"
python -m pytest -q tests/test_vnext_readiness.py tests/test_vnext_release_readiness.py
```


## Gate de segurança LLM na camada query_service

`query_agent()` agora aplica o mesmo princípio fail-closed mesmo quando chamado diretamente por Python/CLI.

### Comportamento
- `data_quality` ausente → LLM bloqueado;
- `has_blocking_divergences=true` → LLM bloqueado;
- `blocking_divergences_n > 0` → LLM bloqueado;
- resposta determinística e pacote RAG continuam disponíveis para diagnóstico;
- LLM só executa quando a qualidade de dados está explicitamente não bloqueante.

O bloco `llm` passa a informar:
- `requested`;
- `executed`;
- `blocked`;
- `block_reason`;
- `safety`.

Execute:
```powershell
$env:PYTHONPATH="src"
python -m pytest -q tests/test_vnext_agent_query.py tests/test_vnext_agent_http.py
```


## Hardening da API local — validação estrita de payload

A camada HTTP passa a validar tipos e limites antes de chamar `query_agent()`.

### Regras
- `question` deve ser string não vazia e ter no máximo 4000 caracteres;
- `scope` deve ser string e ter no máximo 200 caracteres;
- `mode` deve ser string e pertencer ao conjunto permitido;
- `use_llm` deve ser booleano real; strings como `"false"` são rejeitadas;
- falha de validação retorna HTTP 400;
- lógica epidemiológica continua fora da API.

Execute:
```powershell
$env:PYTHONPATH="src"
python -m pytest -q tests/test_vnext_agent_http.py tests/test_vnext_agent_query.py
```


## Segurança da API — bind externo e Bearer token

A API continua segura por padrão em localhost.

### Regras
- `127.0.0.1`, `localhost` e `::1` podem iniciar sem token;
- qualquer bind externo, inclusive `0.0.0.0`, exige `MENINGITES_API_TOKEN`;
- quando o token estiver configurado, `POST /v1/query` exige `Authorization: Bearer <token>`;
- comparação de token usa `hmac.compare_digest`;
- `/health` permanece disponível para observabilidade local;
- bind externo ainda não substitui TLS/autorização institucional para produção.

### Exemplo local
```powershell
$env:PYTHONPATH="src"
python pipelines/vnext_agent_api.py --outdir saida_meningites_v17 --host 127.0.0.1 --port 8765
```

### Exemplo de laboratório com bind externo protegido
```powershell
$env:MENINGITES_API_TOKEN="<segredo-forte-local>"
python pipelines/vnext_agent_api.py --outdir saida_meningites_v17 --host 0.0.0.0 --port 8765
```

Execute:
```powershell
python -m pytest -q tests/test_vnext_agent_http.py
```

- O endpoint `/health` informa `auth_required=true|false`, sem expor token ou segredo.


## Manifesto operacional consolidado

Depois de gerar os demais gates, publique também:

```powershell
$env:PYTHONPATH="src"
python pipelines/vnext_operational_manifest.py --outdir saida_meningites_v17
```

Saídas:
- `manifesto_operacional_vnext.json`;
- `MANIFESTO_OPERACIONAL_VNEXT.md`.

O manifesto reúne em um único snapshot:
- status da validação;
- preflight;
- evidência;
- readiness;
- release readiness;
- qualidade dos dados;
- política de execução determinística/RAG/LLM;
- política normativa fail-closed;
- política de segurança da API.

### Regra
O manifesto é descritivo e auditável. Ele não altera gates nem autoriza execução; apenas consolida o estado operacional já calculado pelos componentes canônicos.


## Registro central de schemas e compatibilidade

O VNext passa a usar `src/meningites/domain/schema_registry.py` como referência canônica de versões aceitas.

### Contratos registrados
- `agent_context` → `agent-context-vnext-1`;
- `rag_request` → `rag-request-vnext-1`;
- `llm_response` → `llm-response-vnext-2`;
- `validation` → `vnext-validation-1`;
- `validation_evidence` → `vnext-validation-evidence-1`;
- `preflight` → `vnext-preflight-1`;
- `readiness` → `vnext-readiness-1`;
- `release_readiness` → `vnext-release-readiness-1`;
- `operational_manifest` → `vnext-operational-manifest-1`.

### Regras
1. Consumidores críticos devem chamar `require_schema()` antes de interpretar payloads versionados.
2. Versão desconhecida ou ausente deve falhar explicitamente.
3. Uma nova versão só entra em `accepted` após adapter/migração/testes documentados.
4. Não alterar `current` sem ADR/Agent Review.
5. Publicar o catálogo local com:

```powershell
$env:PYTHONPATH="src"
python pipelines/vnext_schema_catalog.py --outdir saida_meningites_v17
```

Saída:
- `catalogo_schemas_vnext.json`.

Execute:
```powershell
python -m pytest -q tests/test_vnext_schema_registry.py tests/test_vnext_operational_agent.py tests/test_vnext_structured_llm.py
```


## Compatibilidade de schema nos gates finais

O schema registry agora é aplicado também aos artefatos consumidos por:
- captura de evidência;
- preflight;
- readiness;
- release readiness;
- manifesto operacional.

### Regra fail-closed
Mesmo que um JSON contenha campos aparentemente válidos e status `PASS`, ele deve ser rejeitado/bloqueado se `schema_version` estiver ausente ou incompatível.

### Consequências
- evidência não é capturada sobre validação de schema desconhecido;
- preflight interrompe se `validacao_vnext.json` tiver schema incompatível;
- readiness não chega a READY com artefatos de versões não aceitas;
- release readiness permanece bloqueado;
- manifesto mostra `schema_compatibility` por artefato e bloqueia LLM quando contexto/validação são incompatíveis.

Execute:
```powershell
$env:PYTHONPATH="src"
python -m pytest -q tests/test_vnext_schema_registry.py tests/test_vnext_validation_evidence.py tests/test_vnext_preflight.py tests/test_vnext_readiness.py tests/test_vnext_release_readiness.py tests/test_vnext_operational_manifest.py
```


## Consistência de snapshot/commit

Os gates finais passam a ser vinculados ao commit efetivamente validado.

### Regras
1. `preflight_vnext.json` registra `commit_sha`.
2. `evidencia_validacao_vnext.json` registra o mesmo `commit_sha`.
3. A revisão visual deve registrar explicitamente o commit revisado:

```powershell
python pipelines/vnext_record_visual_review.py `
  --outdir saida_meningites_v17 `
  --reviewer "Menandes" `
  --approved `
  --commit <SHA_DO_COMMIT> `
  --notes "Dashboard e cards revisados localmente."
```

4. `vnext_readiness.py` exige que preflight, evidência e revisão visual tenham SHAs não vazios e idênticos.
5. Quando consistente, `prontidao_vnext.json` publica `snapshot_commit`.
6. `vnext_release_readiness.py --commit <SHA>` só pode retornar apto se `<SHA>` for exatamente igual ao `snapshot_commit` aprovado.

### Motivo
Evitar que um conjunto de dados seja hashado em um commit e visualmente aprovado em outro, ou que o relatório final declare pronto um snapshot diferente daquele efetivamente revisado.


## Cadeia de custódia do snapshot

Depois de gerar preflight, evidência, revisão visual e readiness, publique:

```powershell
$env:PYTHONPATH="src"
python pipelines/vnext_snapshot_chain.py --outdir saida_meningites_v17
```

Saídas:
- `cadeia_custodia_vnext.json`;
- `CADEIA_CUSTODIA_VNEXT.md`.

A cadeia consolida:
- `snapshot_commit`;
- commits registrados em evidência/preflight/revisão visual/readiness;
- compatibilidade de schemas;
- revisor e momento da revisão;
- hashes SHA-256 dos artefatos canônicos;
- status de readiness/release readiness.

### Regra
`custody_ok=true` exige:
- schemas compatíveis;
- commits não vazios e idênticos entre evidência, preflight, revisão visual e readiness;
- pelo menos um artefato hashado;
- revisão visual aprovada com revisor;
- readiness em `ready=true`.

A cadeia é derivada e auditável; não substitui os gates nem a decisão humana de merge.


## Teste ponta a ponta do snapshot

A suíte inclui `tests/test_vnext_snapshot_e2e.py`, que valida em sequência:
- validação PASS;
- contexto com data quality segura;
- preflight com commit;
- evidência com hashes e o mesmo commit;
- revisão visual vinculada ao mesmo commit;
- readiness READY com `snapshot_commit`;
- release readiness para o mesmo commit;
- cadeia de custódia com `custody_ok=true`.

Também cobre cenário negativo em que a revisão visual pertence a outro commit e deve bloquear READY.

Execute:
```powershell
$env:PYTHONPATH="src"
python -m pytest -q tests/test_vnext_snapshot_e2e.py
```
