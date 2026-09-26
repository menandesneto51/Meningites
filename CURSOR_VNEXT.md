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
