# Base única SINAN — fonte DW V23

**Fonte:** `DW_VW_SINAN_MENINGITE` ← `sinan_meningites_dw.csv`
**Residentes MT:** 5944 casos | **Colunas:** 186
**Gerado em:** 27/07/2026 11:36

## Auditoria DW × local

- Local (`meningite.csv`): 5925 linhas
- DW (`VW_SINAN_MENINGITE`): 6032 linhas
- Overlap notificações: 5894
- Somente no DW: **109** (ver `auditoria_sinan_somente_dw_v23.csv`)
- Somente no local: 2

## Como forçar fonte

```powershell
$env:MENINGITES_SINAN_SOURCE='dw'     # só DW
$env:MENINGITES_SINAN_SOURCE='local'  # só CSV legado
$env:MENINGITES_SINAN_SOURCE='auto'   # DW se existir (padrão)
py -3.13 00_base_unica_meningites_v17.py
```
