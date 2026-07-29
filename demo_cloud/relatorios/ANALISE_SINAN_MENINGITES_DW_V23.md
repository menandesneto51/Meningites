# Análise da base SINAN Meningites (DW) — MT

**Fonte:** `dbo.VW_SINAN_MENINGITE` · **Ref.:** 26/07/2026  
**Universo:** 5.944 residentes MT (após filtro `UfResidencia=MT`)

## Achado crítico (corrigido)

O parser `dayfirst=True` **invertia mês/dia** em datas ISO do DW (`2026-06-12` → `2026-12-06`).  
Corrigido em `00_base_unica_meningites_v17.py` (`parse_dates_smart`). Pós-correção: **0** datas futuras e **0** sintomas após notificação.

## Indicadores MS (toda a base)

| Indicador | MT | Meta BR 2024 |
|---|---:|---:|
| Lab PCR/cultura | **44,4%** | 36,1% |
| Investigados ≤48h | 93,6% | 97,8% |
| Encerrados ≤60d | 83,6% | 94,4% |
| Quimio DM ≤48h | 35,3% | 45,5% |

## Perfil

- Confirmados 3.495 · Descartados 1.911 · Óbitos meningite 395 · DM 278  
- 2025: 246 · 2026 (até 11/07): 173  
- Completude fraca: PCR líquor (~21%), quimio (~11%), sorogrupo NM (~1,4% da base / ~31% na DM)  
- 57 linhas com `NumeroNotificacao` duplicado · 15 registros pré-2007  
- 251 linhas com valor atípico em `ClassificacaoCaso` (“Meningite por outra etiologia”)

## Top municípios 2024–2026

Cuiabá (155), Várzea Grande (67), Sinop (60), Rondonópolis (53).