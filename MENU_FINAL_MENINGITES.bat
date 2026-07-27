@echo off
chcp 65001 >nul
title Robo de Meningites CIEVS-MT — Menu
cd /d "%~dp0"

echo ============================================================
echo  ROBO DE MENINGITES — CIEVS-MT (menu operacional)
echo ============================================================
echo.
echo  [1] Atualizar tudo do DW (ops semanal)
echo  [2] Atualizar + regenerar demo_cloud (para upar Cloud)
echo  [3] Pipeline V23 + abrir painel
echo  [4] So abrir painel (http://localhost:8510)
echo  [5] Validar saidas
echo  [6] Pipeline completo pesquisa (--all --from-dw)
echo  [7] Instalar dependencias locais
echo  [0] Sair
echo.

set /p OPCAO=Digite a opcao: 

if "%OPCAO%"=="1" (
    call "%~dp0ATUALIZAR_MENINGITES.bat"
    goto FIM
)
if "%OPCAO%"=="2" (
    call "%~dp0ATUALIZAR_MENINGITES.bat" --cloud
    goto FIM
)
if "%OPCAO%"=="3" (
    call "%~dp0RODAR_MENINGITES_V23.bat"
    goto FIM
)
if "%OPCAO%"=="4" (
    call "%~dp0ABRIR_PAINEL_MENINGITES.bat"
    goto FIM
)
if "%OPCAO%"=="5" (
    py -3.13 pipeline_meningites_v23_indicadores_ms.py --validate
    pause
    goto FIM
)
if "%OPCAO%"=="6" (
    py -3.13 pipeline_meningites_v23_indicadores_ms.py --all --from-dw
    if errorlevel 1 pause
    pause
    goto FIM
)
if "%OPCAO%"=="7" (
    call "%~dp000_INSTALAR_DEPENDENCIAS_MENINGITES_V17.bat"
    goto FIM
)
if "%OPCAO%"=="0" exit /b 0

echo Opcao invalida.
pause

:FIM
