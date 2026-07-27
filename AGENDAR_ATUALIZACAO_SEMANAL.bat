@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Agendar atualizacao semanal Meningites

echo ============================================================
echo  Agenda Task Scheduler — atualizacao semanal Meningites
echo  Padrao: toda SEGUNDA as 07:00
echo ============================================================
echo.

set TASK=CIEVS_Meningites_Atualizacao_Semanal
set BAT=%~dp0ATUALIZAR_MENINGITES.bat
set LOGDIR=%~dp0logs_orquestrador
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

echo Removendo tarefa antiga (se existir)...
schtasks /Delete /TN "%TASK%" /F >nul 2>&1

echo Criando tarefa...
schtasks /Create /TN "%TASK%" /TR "\"%BAT%\"" /SC WEEKLY /D MON /ST 07:00 /RL LIMITED /F
if errorlevel 1 (
  echo.
  echo [ERRO] Nao foi possivel criar a tarefa. Execute este BAT como usuario
  echo        com permissao no Agendador de Tarefas.
  pause
  exit /b 1
)

echo.
echo [OK] Tarefa criada: %TASK%
echo     Comando: %BAT%
echo     Quando: segundas 07:00
echo.
echo Para incluir demo_cloud automaticamente, edite a tarefa e use:
echo   ATUALIZAR_MENINGITES.bat --cloud
echo.
echo Ver: schtasks /Query /TN "%TASK%" /V /FO LIST
pause
