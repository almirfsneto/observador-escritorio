@echo off
setlocal
chcp 65001 >nul
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -X utf8 "%~dp0tools\validar_laboratorio.py"
  goto fim
)
where python >nul 2>nul
if not errorlevel 1 (
  python -X utf8 "%~dp0tools\validar_laboratorio.py"
  goto fim
)
echo Python 3.11+ com Tk nao foi encontrado. Peca ao TI para instalar previamente.
echo Este lancador nao instala dependencias nem solicita administrador.
:fim
if errorlevel 1 pause
endlocal
