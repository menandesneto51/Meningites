@echo off
chcp 65001 >nul
title Instalar dependencias Meningites CIEVS-MT
cd /d "%~dp0"

echo Instalando stack local com Python 3.13...
echo   - requirements.txt        (painel + geo basico)
echo   - requirements-full.txt   (pipeline pesado + DW/pyodbc)
echo.
echo Requisito DW: ODBC Driver 18 for SQL Server
echo.

set PIP_REQUIRE_VIRTUALENV=0
py -3.13 -m pip install --upgrade pip
if errorlevel 1 (
  echo [ERRO] Python 3.13 nao encontrado. Instale e use: py -3.13 --version
  pause
  exit /b 1
)

py -3.13 -m pip install -r requirements.txt
py -3.13 -m pip install -r requirements-full.txt

echo.
echo [OK] Dependencias instaladas.
py -3.13 -c "import pandas,streamlit,geopandas,pyodbc; print('imports OK')"
pause
