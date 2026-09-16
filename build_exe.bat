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

echo Instalando dependencias e o PyInstaller...
%PY% -m pip install --quiet --disable-pip-version-check -r requirements.txt "pyinstaller>=6.10,<7"
if errorlevel 1 (
    echo Falha ao instalar as dependencias.
    pause
    exit /b 1
)

echo Gerando o executavel (pode levar alguns minutos)...
%PY% -m PyInstaller --noconfirm --clean --onedir --name BuscadorDeDesenhos ^
    --add-data "app.py;." ^
    --add-data "core_logic.py;." ^
    --collect-all streamlit ^
    --collect-all pdfplumber ^
    --copy-metadata streamlit ^
    --hidden-import streamlit.runtime.scriptrunner.magic_funcs ^
    launcher.py
if errorlevel 1 (
    echo Falha ao gerar o executavel.
    pause
    exit /b 1
)

echo.
echo Executavel criado em: dist\BuscadorDeDesenhos\BuscadorDeDesenhos.exe
echo Crie um atalho desse arquivo na Area de Trabalho para os usuarios finais.
pause
