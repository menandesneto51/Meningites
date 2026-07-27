@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Abrindo painel MENINGITES em http://localhost:8510
echo (porta dedicada — nao confundir com Clima-Saude em 8501)
py -3.13 -m streamlit run dashboard_meningites_v22_refinado.py --server.port 8510 --browser.gatherUsageStats false
