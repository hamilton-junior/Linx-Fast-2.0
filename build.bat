@echo off
chcp 65001 >nul

python generate_version.py

REM Obtém o caminho curto para a Área de Trabalho (Desktop)
for %%I in ("C:\OneDrive\OneDrive - Linx SA\Área de Trabalho") do set "DESKTOP_SHORT=%%~sI"

REM Mostra o caminho curto para depuração
echo Caminho curto da Área de Trabalho: %DESKTOP_SHORT%

REM Cria as pastas de saída se não existirem
if not exist "%DESKTOP_SHORT%\LinxFast2.0" mkdir "%DESKTOP_SHORT%\LinxFast2.0"
if not exist "%DESKTOP_SHORT%\build" mkdir "%DESKTOP_SHORT%\build"

python -m PyInstaller --onefile --noconsole --icon="LinxFast2.ico" --add-data="templates;templates" --distpath="%DESKTOP_SHORT%\LinxFast2.0" --workpath="%DESKTOP_SHORT%\build" app.py
pause