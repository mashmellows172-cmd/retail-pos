@echo off
title RetailPOS Pro - Build
echo.
echo  =========================================
echo   RetailPOS Pro - Generando ejecutable...
echo  =========================================
echo.

pip install pyinstaller --quiet

pyinstaller --onefile --windowed --name "RetailPOS Pro" ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --hidden-import flask ^
  --hidden-import pandas ^
  --hidden-import openpyxl ^
  --hidden-import barcode ^
  --hidden-import barcode.writer ^
  app.py

echo.
echo [OK] Ejecutable generado en: dist\RetailPOS Pro.exe
echo Copia ese archivo junto con tu Excel y ejecutalo directamente.
pause
