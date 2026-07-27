@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo  Robo Meningites CIEVS-MT — V23
echo  Painel: http://localhost:8510
echo  (NAO use 8501 — essa porta e do Clima)
echo ========================================
echo.
py -3.13 pipeline_meningites_v23_indicadores_ms.py --only-v23 --open-dashboard
if errorlevel 1 (
  echo.
  echo [ERRO] Falha ao executar. Verifique se o Python 3.13 esta instalado:
  echo   py -3.13 --version
  pause
)
