# Governança por Agentes — Meningites

Este projeto usa revisão multiagente como gate de engenharia e epidemiologia.

## Fluxo obrigatório

1. **CTO Virtual** — recebe a mudança, define especialistas aplicáveis e verifica gates.
2. **Product Owner** — explicita problema, usuário, valor, backlog e critérios de aceite.
3. **Clinical/Epidemiological Specialist** — valida definições, indicadores e recomendações contra fontes oficiais vigentes. Não cria regra clínica.
4. **Data Architect** — valida fonte, granularidade, modelo, contratos, lineage, temporalidade e qualidade.
5. **Chief Architect** — valida limites de domínio, dependências, ADRs, compatibilidade e dívida técnica.
6. **Security/LGPD** — verifica minimização, PII, pseudonimização, segredos, perfis e auditoria.
7. **QA/Data Quality** — testa contratos, consistência, regressão, dados ausentes e casos extremos.
8. **DevOps/Observability** — valida configuração, execução, logs, falhas, reprodutibilidade e implantação.
9. **UX/Decision Support**, quando houver interface — valida legibilidade, hierarquia, explicabilidade e ação possível.
10. **CTO Virtual** — fecha o gate somente com evidências dos especialistas aplicáveis.

## Definition of Done

Uma mudança que afeta regra, dado ou decisão epidemiológica só está concluída quando:

- critérios de aceite estão explícitos;
- fonte e vigência estão registradas quando aplicável;
- contrato de entrada/saída está testado;
- procedência é rastreável;
- não há segredo ou PII indevida no artefato;
- falhas críticas são observáveis;
- regressão foi testada;
- impacto operacional foi documentado;
- documentação foi atualizada.

## Registro

Mudanças relevantes devem manter em PR/ADR um bloco `Agent Review` com:
- agentes aplicados;
- achados;
- riscos;
- decisões;
- evidências/testes;
- pendências aceitas.

A governança por agentes complementa — não substitui — revisão humana, protocolos oficiais e governança institucional.
