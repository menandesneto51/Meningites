# Hospedar no Streamlit Community Cloud

## O que sobe
- Código do painel (`dashboard_meningites_v22_refinado.py`)
- Pacote **demo anonimizado** em `demo_cloud/` (sem nome/CNS/endereço)
- Shapefile municipal
- **Sem** conexão ao Data Warehouse da SES-MT

## Preparar pacote (na máquina local, após rodar o pipeline)
```bat
py -3.13 preparar_pacote_cloud_demo.py
git add demo_cloud requirements.txt packages.txt runtime.txt
git commit -m "Add Streamlit Cloud demo pack"
git push
```

## Publicar
1. Acesse https://share.streamlit.io (conta GitHub)
2. **New app** → repositório `menandesneto51/Meningites` (privado OK se autorizar)
3. Branch: `main`
4. Main file: `dashboard_meningites_v22_refinado.py`
5. Deploy

URL típica: `https://<nome-do-app>.streamlit.app`

## Avaliadores de outro estado
- Compartilhe o link público do app
- Ou deixe o app **private** no Streamlit Cloud e convide por e-mail

## Limitações do cloud
- Sem DW / GAL / SIM ao vivo
- Dados do último pacote demo gerado
- Forecast/nowcast são os já calculados localmente

## Local (porta dedicada Meningites)
```bat
ABRIR_PAINEL_MENINGITES.bat
```
http://localhost:8510
