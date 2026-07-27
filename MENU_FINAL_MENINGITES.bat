@echo off
chcp 65001 > nul
title Robo de Meningites - Menu Final
cd /d "%~dp0"

echo ============================================================
echo ROBO DE MENINGITES - MENU FINAL
echo ============================================================
echo.
echo [1] Rodar pipeline completo
echo [2] Abrir dashboard por abas
echo [3] Gerar relatorio Word
echo [4] Rodar pipeline + gerar Word + abrir dashboard
echo [5] Apenas auditar saidas existentes
echo [0] Sair
echo.

set /p OPCAO=Digite a opcao: 

if "%OPCAO%"=="1" (
    python orquestrador_meningites.py --run-all
    goto FIM
)

if "%OPCAO%"=="2" (
    python -m streamlit run dashboard_meningites_abas.py
    goto FIM
)

if "%OPCAO%"=="3" (
    python gerar_relatorio_word_meningites.py
    goto FIM
)

if "%OPCAO%"=="4" (
    python orquestrador_meningites_final.py --everything
    goto FIM
)

if "%OPCAO%"=="5" (
    python orquestrador_meningites.py --audit-only
    goto FIM
)

if "%OPCAO%"=="0" (
    exit /b 0
)

echo Opcao invalida.

:FIM
echo.
echo Processo finalizado.
pause
