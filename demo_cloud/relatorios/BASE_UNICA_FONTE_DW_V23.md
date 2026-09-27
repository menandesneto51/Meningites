# Base única SINAN — fonte DW V23

**Fonte:** `DW_VW_SINAN_MENINGITE` ← `sinan_meningites_dw.csv`
**Residentes MT:** 6004 casos | **Colunas:** 186
**Gerado em:** 27/09/2026 10:08

## Como forçar fonte

```powershell
$env:MENINGITES_SINAN_SOURCE='dw'     # só DW
$env:MENINGITES_SINAN_SOURCE='local'  # só CSV legado
$env:MENINGITES_SINAN_SOURCE='auto'   # DW se existir (padrão)
py -3.13 00_base_unica_meningites_v17.py
```