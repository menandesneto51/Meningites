# Motor de Situação Epidemiológica Municipal — VNext

## Propósito

Converter indicadores municipais já calculados em sinais operacionais explicáveis e priorizáveis, sem misturar cálculo epidemiológico, regra normativa e apresentação.

## Contrato

Entrada: `MunicipalSnapshot` com código/nome do município, métricas e evidências.

Regra: `SignalRule` versionável, contendo métrica, operador, limiar, categoria, prioridade, descrição, ações sugeridas e, quando aplicável, referência normativa + vigência.

Saída: `OperationalSignal`, sempre contendo gatilho e evidência.

## Integração inicial planejada

- módulo 12: indicadores operacionais MS;
- módulo 20: fila CIEVS e reconciliação;
- módulo 26: indicadores operacionais avançados;
- módulo 32: GAL/tipagem;
- módulo 33: SIH;
- módulo 34: vacinação;
- módulo 35: RedCap, quando houver fonte real.

## Gate epidemiológico

Os exemplos de teste não constituem limiares clínicos ou epidemiológicos. Regras de produção só podem ser ativadas depois de:
1. mapear o indicador real e seu denominador;
2. identificar fonte oficial vigente quando a regra for normativa;
3. registrar regra e versão;
4. testar contra artefato histórico;
5. validar com especialista epidemiológico;
6. documentar impacto esperado e possibilidade de falso sinal.

## Próximo incremento

Criar catálogo de regras de produção a partir dos indicadores já implementados e um agregador municipal que leia os artefatos dos módulos 12/20/26/32–35, mantendo compatibilidade com o pipeline atual.
