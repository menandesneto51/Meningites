# CNES / SINASC — enriquecimento V30

**Gerado em:** 27/09/2026 10:11

## Escopo

- **CNES:** perfil da unidade notificante (tipo, esfera, regional) cruzado com SINAN.
- **Proxy de acesso:** % de casos notificados em alta complexidade vs atenção básica, por regional (complementa a distância a Cuiabá).
- **SINASC:** nascidos vivos como denominador para proxy de incidência em <1 ano. Linkage nominal mãe–caso **não** é feito (utilidade epidemiológica fraca / LGPD).

- CNES disponível: **sim**
- SINASC disponível: **sim**

## Resumo estadual (CNES)

- Match CNES: **92.1%** (5529/6004)
- Alta complexidade / hospitalar: **90.0%**
- Atenção básica: **1.5%**
- Unidades distintas: **243**

## Proxy de acesso por regional

Ver `cnes_acesso_complexidade_regional_v30.csv`.

## Top tipos de unidade notificante

- HOSPITAL GERAL: 4729 casos (Alta complexidade / hospitalar)
- Sem match/sem tipo: 475 casos (Sem match CNES)
- HOSPITAL ESPECIALIZADO: 388 casos (Alta complexidade / hospitalar)
- PRONTO ATENDIMENTO: 228 casos (Alta complexidade / hospitalar)
- CENTRO DE SAUDE/UNIDADE BASICA: 81 casos (Atenção básica)
- CLINICA/CENTRO DE ESPECIALIDADE: 40 casos (Alta complexidade / hospitalar)
- CENTRAL DE GESTAO EM SAUDE: 30 casos (Outros / intermediário)
- PRONTO SOCORRO GERAL: 10 casos (Alta complexidade / hospitalar)

## SINASC

- Nascidos vivos agregados: **207486** em 4 ano(s) / 142 municípios.

- Linhas município-ano com casos <1 ano: **542** (com NV: 92)
- Arquivo: `incidencia_menor1ano_sinasc_v30.csv`