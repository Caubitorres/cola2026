@echo off
cd /d "%~dp0"
echo TESTE: baixando somente 10 fotos...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0baixar-fotos.ps1" -Limite 10
echo.
pause
