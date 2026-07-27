@echo off
chcp 65001 > nul
title Instalar dependencias Meningites V17
cd /d "%~dp0"
python -m pip install --upgrade pip
python -m pip install -r requirements_meningites_v17.txt
pause
