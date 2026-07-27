@echo off
chcp 65001 > nul
title Gerar Relatorio Word - Meningites
cd /d "%~dp0"
python gerar_relatorio_word_meningites.py
pause
