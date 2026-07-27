@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Atualizar Meningites CIEVS-MT

echo ============================================================
echo  ATUALIZACAO OPERACIONAL — Meningites CIEVS-MT
echo  1) Extrai DW + base unica
echo  2) Roda indicadores MS / alertas / fila / nowcast V24
echo  3) Valida artefatos (falha se faltar critico)
echo  4) Opcional: regenera demo_cloud para Streamlit Cloud
echo ============================================================
echo.
echo Painel local: http://localhost:8510
echo.

set CLOUD=
if /I "%~1"=="--cloud" set CLOUD=1
if /I "%~1"=="/cloud" set CLOUD=1

echo [1/3] Pipeline operacional (--ops --from-dw)...
py -3.13 pipeline_meningites_v23_indicadores_ms.py --ops --from-dw
if errorlevel 1 (
  echo.
  echo [ERRO] Pipeline falhou. Verifique .env / DW / Python 3.13.
  pause
  exit /b 1
)

echo.
echo [2/3] Validacao...
py -3.13 pipeline_meningites_v23_indicadores_ms.py --validate
if errorlevel 1 (
  echo.
  echo [ERRO] Validacao incompleta — revise os arquivos [AUSENTE].
  pause
  exit /b 1
)

if defined CLOUD (
  echo.
  echo [3/3] Pacote demo_cloud...
  py -3.13 preparar_pacote_cloud_demo.py
  if errorlevel 1 (
    echo [ERRO] Falha ao gerar demo_cloud.
    pause
    exit /b 1
  )
  echo.
  echo Proximo passo Cloud:
  echo   git add demo_cloud
  echo   git commit -m "Refresh demo_cloud"
  echo   git push
) else (
  echo.
  echo [3/3] demo_cloud pulado. Para Cloud use:
  echo   ATUALIZAR_MENINGITES.bat --cloud
)

echo.
echo [OK] Atualizacao operacional concluida.
echo Abrir painel? ^(S/N^)
set /p ABRIR=
if /I "%ABRIR%"=="S" (
  start "" "%~dp0ABRIR_PAINEL_MENINGITES.bat"
)
pause
