# LEIA-ME — Robô de Meningites CIEVS-MT (V23)

## Painel (Meningites — porta dedicada)

**URL correta:** http://localhost:8510  

Não use a porta **8501** — ela costuma estar ocupada pelo **SIS Integrado Clima-Saúde** (`dashboard_titan.py`).

```bat
ABRIR_PAINEL_MENINGITES.bat
```

Ou:

```powershell
py -3.13 -m streamlit run dashboard_meningites_v22_refinado.py --server.port 8510
```

Use **Python 3.13** neste ambiente (o 3.12 padrão pode não ter numpy/pandas).

## O que o V23 entrega

| Módulo | Função |
|---|---|
| 12 | Indicadores oficiais MS (lab, 48h, 60d, quimio) |
| 13 | Alertas inteligentes + NT 154/2024 |
| 14 | Painel epidemiológico (incidência/mortalidade/letalidade) |
| 15 | Boletim semanal (rascunho) |
| 16 | Assistente CIEVS (RAG normas + narrativa) |
| 17 | Linkage GAL/LACEN/SIM (DW + proxy SINAN) |
| 18 | Arquivamento de versões legadas |
| 19 | Extração DW SES/MT (`VW_SINAN_MENINGITE`, `VW_GAL`, `SIM`, `SINASC`, CNES) |
| 20 | Enriquecimento GAL/SIM + fila CIEVS unificada |
| 21 | Sazonalidade (índice mensal, heatmap SE×ano) |
| 22 | Nowcast com atraso de notificação + forecast semanal + backtest |
| 23 | Alertas personalizados (digests regional/lab) + narrativa IA |
| 24 | Nowcast operacional + indicadores de gestão da semana |
| 25/26 | Ops avançados: quimio Hib, backlog, linkage, sorogrupos, score NT154, PL/vacina, boletim envio |

Dashboard atual: `dashboard_meningites_v22_refinado.py` (abas V23/V24/V25 + Clima×casos exploratório).

## Rotina operacional (preferencial)

```bat
ATUALIZAR_MENINGITES.bat
ATUALIZAR_MENINGITES.bat --cloud
MENU_FINAL_MENINGITES.bat
AGENDAR_ATUALIZACAO_SEMANAL.bat
```

Modos do pipeline:

| Flag | Uso |
|------|-----|
| `--ops --from-dw` | Rotina semanal (MS, alertas, fila, gestão V24) — **fail-closed** em linkage/fila |
| `--research --from-dw` | Completo (OR, Moran, clima, lab, vacina + V23) |
| `--validate` | Contratos de artefatos (exit 1 se faltar crítico) |
| `--only-v23` | Alias de `--ops` |
| `--all` | Alias de `--research` |

Testes de contrato:

```powershell
py -3.13 -m unittest tests.test_contratos_ops -v
```

Fluxo semanal oficial:
1. Extrai DW + regenera base
2. Roda módulos MS / alertas / fila / nowcast V24
3. Valida artefatos críticos (exit ≠ 0 se faltar)
4. Com `--cloud`, regenera `demo_cloud/` (+ GeoJSON simplificado) para push no GitHub/Streamlit Cloud

Instalação local (Python 3.13 + ODBC Driver 18):

```bat
00_INSTALAR_DEPENDENCIAS_MENINGITES_V17.bat
```

## Sazonalidade, nowcast e alertas personalizados

```powershell
py -3.13 21_sazonalidade_meningites_v23.py
py -3.13 22_nowcast_forecast_refinado_v23.py
py -3.13 23_alertas_personalizados_ia_v23.py
```

No painel: aba **09** (sazonalidade + canal), **10** (nowcast refinado + projeções), **03** (fila + digests regionais).
Digests em `saida_meningites_v17/digests_regionais_v23/`.

## Data Warehouse SES/MT (mesmo acesso dos outros projetos CIEVS)

Host `10.15.1.50` · DB `Datawarehouse`. Credenciais via `.env` de **Ondas de calor** / **Clima-Saúde** (ou `DW_ENV_FILE` — ver `.env.example`).

```powershell
py -3.13 19_dw_descobrir_e_extrair_v23.py
```

Views/tabelas confirmadas:
- `dbo.VW_SINAN_MENINGITE`
- `dbo.VW_GAL` (GAL/LACEN)
- `dbo.SIM` / `dbo.SINASC` / `dbo.VW_SINASC`
- `dbo.CNES_ESTABELECIMENTOS` (+ outras CNES)

## Linkage GAL / LACEN / SIM

1. Rode o extrator DW (acima) — grava em `entradas_linkage/`.
2. Rode `py -3.13 17_linkage_gal_lacen_sim_v23.py`.
3. Consulte `relatorios/LINKAGE_GAL_LACEN_SIM_V23.md` e `relatorios/DW_EXTRACAO_MENINGITES_V23.md`.

Se o DW estiver offline, o sistema mantém o **proxy interno** do SINAN.

## Fonte canônica SINAN

Prioridade automática: `entradas_linkage/sinan_meningites_dw.csv` (`dbo.VW_SINAN_MENINGITE`).
Fallback: `meningite.csv` local.

Atualizar base a partir do DW:

```powershell
py -3.13 pipeline_meningites_v23_indicadores_ms.py --from-dw
# ou só módulos V23 com base nova:
py -3.13 pipeline_meningites_v23_indicadores_ms.py --only-v23 --from-dw
```

Forçar fonte: `$env:MENINGITES_SINAN_SOURCE='dw'|'local'|'auto'`

## Arquivar legado

Dry-run:

```powershell
py -3.13 18_arquivar_legado_v23.py --dry-run
```

Aplicar (move para `_arquivo_legado/`, não apaga):

```powershell
py -3.13 18_arquivar_legado_v23.py --apply
```

## Validação

```powershell
py -3.13 pipeline_meningites_v23_indicadores_ms.py --validate
```

Retorna código de saída **1** se faltar artefato crítico (base, indicadores MS, fila, gestão V24).
