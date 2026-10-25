@echo off
chcp 65001 >NUL
cd /d "%~dp0"
title Caso Red Electrica - instalacion y arranque
rem El solver HiGHS aun no tiene version para Python 3.15: se usa Python 3.12 en un entorno propio (.venv)
where py >NUL 2>NUL || (echo No se encuentra el lanzador "py" de Python. Instale Python desde python.org & pause & exit /b 1)
py -3.12 --version >NUL 2>NUL
if errorlevel 1 (
  echo [0/3] Instalando Python 3.12 junto a su Python actual. Si pregunta algo, responda Y y pulse Enter.
  py install 3.12
)
if not exist ".venv\Scripts\python.exe" (
  echo Creando el entorno del proyecto...
  py -3.12 -m venv .venv
)
set PY=.venv\Scripts\python.exe
set PYTHONIOENCODING=utf-8
if not exist "%PY%" (echo ERROR: no se pudo crear el entorno con Python 3.12. & pause & exit /b 1)
echo [1/3] Instalando librerias (solo tarda la primera vez, 1-3 minutos)...
"%PY%" -m pip install --upgrade pip > registro_instalacion.txt 2>&1
"%PY%" -m pip install -r requirements.txt >> registro_instalacion.txt 2>&1
if errorlevel 1 (echo ERROR instalando librerias. Ver registro_instalacion.txt & pause & exit /b 1)
echo [2/3] Comprobando el modelo (validacion)...
"%PY%" validacion.py > registro_validacion.txt 2>&1
type registro_validacion.txt
echo.
echo [3/3] Abriendo la herramienta en el navegador. Para cerrarla, cierre esta ventana.
"%PY%" -m streamlit run app.py
pause
