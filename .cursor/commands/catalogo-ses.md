# Buscar no Catálogo Mestre SES-MT

Execute:
```powershell
.\scripts\catalogo-ses.ps1 -Query "<necessidade de dados>"
```

Retorne fontes, objetos, campos, PII/sensibilidade, `catalog_health`, ranking, limitações e próximo passo.
Se houver fonte existente, não criar coletor novo antes de DATA_GUARDIAN/DATAOPS.
Se não houver match com catálogo parcial/ausente, atualizar o inventário antes de propor nova fonte.
