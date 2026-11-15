@echo off
title RetailPOS Pro
color 0A
echo.
echo  =========================================
echo   RetailPOS Pro - Iniciando...
echo  =========================================
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instalalo desde python.org
    pause
    exit /b 1
)

REM Instalar dependencias si no están
echo Verificando dependencias...
pip install -r requirements.txt --quiet --disable-pip-version-check

echo.
echo Abriendo dashboard en el navegador...
echo Cierra esta ventana para apagar la aplicacion.
echo.

REM Lanzar Flask
python app.py

pause
