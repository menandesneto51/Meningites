# CNES / SINASC — enriquecimento V30

**Gerado em:** 30/07/2026 09:54

## Escopo

- **CNES:** perfil da unidade notificante (tipo, esfera, regional) cruzado com SINAN.
- **Proxy de acesso:** % de casos notificados em alta complexidade vs atenção básica, por regional (complementa a distância a Cuiabá).
- **SINASC:** nascidos vivos como denominador para proxy de incidência em <1 ano. Linkage nominal mãe–caso **não** é feito (utilidade epidemiológica fraca / LGPD).

- CNES disponível: **sim**
- SINASC disponível: **sim**

## Resumo estadual (CNES)

- Match CNES: **92.0%** (5470/5944)
- Alta complexidade / hospitalar: **90.0%**
- Atenção básica: **1.4%**
- Unidades distintas: **237**

## Proxy de acesso por regional

Ver `cnes_acesso_complexidade_regional_v30.csv`.

## Top tipos de unidade notificante

- HOSPITAL GERAL: 4681 casos (Alta complexidade / hospitalar)
- Sem match/sem tipo: 474 casos (Sem match CNES)
- HOSPITAL ESPECIALIZADO: 388 casos (Alta complexidade / hospitalar)
- PRONTO ATENDIMENTO: 222 casos (Alta complexidade / hospitalar)
- CENTRO DE SAUDE/UNIDADE BASICA: 77 casos (Atenção básica)
- CLINICA/CENTRO DE ESPECIALIDADE: 40 casos (Alta complexidade / hospitalar)
- CENTRAL DE GESTAO EM SAUDE: 29 casos (Outros / intermediário)
- PRONTO SOCORRO GERAL: 10 casos (Alta complexidade / hospitalar)

## SINASC

- Nascidos vivos agregados: **237440** em 4 ano(s) / 142 municípios.

- Linhas município-ano com casos <1 ano: **542** (com NV: 92)
- Arquivo: `incidencia_menor1ano_sinasc_v30.csv`