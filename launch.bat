@echo off
title RetailPOS Pro v2
color 0B
echo.
echo  ======================================================
echo     RetailPOS Pro v2 - Iniciando PWA Mobile/Desktop
echo  ======================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado en el sistema.
    pause
    exit /b 1
)

echo Iniciando servidor RetailPOS...
start http://localhost:5050
python app.py
pause
