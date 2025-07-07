@echo off
chcp 65001 >nul

python generate_version.py

REM Obtém o caminho curto para a Área de Trabalho (Desktop)
for %%I in ("C:\OneDrive\OneDrive - Linx SA\Área de Trabalho") do set "DESKTOP_SHORT=%%~sI"

REM Mostra o caminho curto para depuração
echo Caminho curto da Área de Trabalho: %DESKTOP_SHORT%

REM Lê a versão e data do arquivo version.py
set VERSION=
set BUILD_DATE=
for /f "usebackq tokens=1,2 delims== " %%A in ("version.py") do (
    if "%%A"=="VERSION" set VERSION=%%B
    if "%%A"=="BUILD_DATE" set BUILD_DATE=%%B
)

REM Remove aspas e espaços extras
set VERSION=%VERSION:"=%
set VERSION=%VERSION: =%
set BUILD_DATE=%BUILD_DATE:"=%
for /f "tokens=1,2 delims= " %%a in ("%BUILD_DATE%") do set BUILD_DATE_ONLY=%%a

REM Monta o nome da pasta de saída
set "DIST_FOLDER=%DESKTOP_SHORT%\LinxFast2.0 - %VERSION% - %BUILD_DATE_ONLY%"

REM Cria as pastas de saída se não existirem
if not exist "%DIST_FOLDER%" mkdir "%DIST_FOLDER%"
if not exist "%DESKTOP_SHORT%\build" mkdir "%DESKTOP_SHORT%\build"

python -m PyInstaller --onefile --noconsole --icon="LinxFast2.ico" --add-data="templates;templates" --distpath="%DIST_FOLDER%" --workpath="%DESKTOP_SHORT%\build" --name="LinxFast2" app.py

REM Cria a pasta de versões, se não existir
set "VERSIONS_FOLDER=%DESKTOP_SHORT%\Linx Fast 2.0 - Versões"
if not exist "%VERSIONS_FOLDER%" mkdir "%VERSIONS_FOLDER%"

REM Move e mescla o conteúdo da pasta de build para a pasta de versões (substitui arquivos se já existir)
robocopy "%DIST_FOLDER%" "%VERSIONS_FOLDER%\%~nxDIST_FOLDER%" /E /MOVE /NFL /NDL /NJH /NJS /NP /R:1 /W:1

REM Remove a pasta de origem se ainda existir (caso robocopy não tenha conseguido mover tudo)
if exist "%DIST_FOLDER%" rmdir /s /q "%DIST_FOLDER%"

pause