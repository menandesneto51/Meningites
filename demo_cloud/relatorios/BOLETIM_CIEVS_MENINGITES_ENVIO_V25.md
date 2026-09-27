# Boletim CIEVS-MT — Meningites (pronta para envio)

**Gerado em:** 27/09/2026 10:11

> Validar com a equipe antes de divulgação oficial.

## Backlog operacional

- Casos abertos: **307**
- Investigação atrasada (>48h): **145**
- Encerramento D45–D60: **7**
- Encerramento >60d: **290**
- Quimio pendente (DM/Hib): **0**
- Hib sem quimio: **11**

## Linkage GAL/SIM

- Match GAL: **4,9%**
- Bacterianas lab+ com GAL: **4,9%**
- Discordância SIM sem óbito SINAN: **20** (0,3%)

## Sorogrupos / NT 154

- Variação de -52.4 p.p. no sorogrupo *Em Branco (2025→2026)
- Variação de 52.4 p.p. no sorogrupo B (2025→2026)

### Municípios com maior score NT154 (90d)
- ACORIZAL (CUIABA): score 0 · DM lab+ 90d=0
- AGUA BOA (AGUA BOA): score 0 · DM lab+ 90d=0
- ALTA FLORESTA (ALTA FLORESTA): score 0 · DM lab+ 90d=0
- ALTO ARAGUAIA (RONDONOPOLIS): score 0 · DM lab+ 90d=0
- ALTO BOA VISTA (SAO FELIX DO ARAGUAIA): score 0 · DM lab+ 90d=0

## Gravidade SE corrente

- SE 35/2026: 2 casos · letalidade 0% · óbitos <7d 0

## Laboratório e vacina (elegíveis)

- pct_pl_realizada_bact_dm: **92,6** — PL realizada em bacterianas/DM
- pct_lab_pendente_bact_dm: **29,9** — Sem resultado PCR/cultura/CIE/látex/bacterioscopia preenchido
- p50_sintomas_pl_dias: **2** — P50 lead sintomas→PL (dias)
- p90_sintomas_pl_dias: **11** — P90 lead sintomas→PL (dias)
- pct_menc_em_dm: **9,0** — DM com Vacina Conjugada Meningo C = Sim
- pct_hib_vac_em_hib: **47,6** — Hib etiológico com vacina Hib = Sim
- pct_pneumo_vac_em_pneumo: **10,7** — Pneumocócica etiológica com vacina pneumo = Sim

## Como atualizar

```bat
ATUALIZAR_MENINGITES.bat
py -3.13 26_indicadores_ops_avancados_v25.py
```