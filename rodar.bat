@echo off
setlocal
cd /d "%~dp0"

set "PY=python"
where py >nul 2>nul
if not errorlevel 1 set "PY=py -3"

%PY% -c "import sys" >nul 2>nul
if errorlevel 1 (
    echo Python nao encontrado. Instale o Python 3.11 ou superior e marque a opcao "Add python.exe to PATH".
    pause
    exit /b 1
)

echo Instalando dependencias...
%PY% -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo Falha ao instalar as dependencias. Verifique a conexao com a internet.
    pause
    exit /b 1
)

echo Iniciando o Buscador de Desenhos...
%PY% -m streamlit run app.py --server.headless=true --server.address=127.0.0.1 --server.enableXsrfProtection=true --server.maxUploadSize=25 --browser.gatherUsageStats=false
pause
