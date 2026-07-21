@echo off
set "APP_DIR=C:\Users\JJHK\Documents\GitHub\Side-quest\converter_app"
set "PYTHONW=C:\Users\JJHK\AppData\Local\Programs\Python\Python312\pythonw.exe"

cd /d "%APP_DIR%"

if not exist "%PYTHONW%" (
    echo Nie znaleziono Pythonw:
    echo %PYTHONW%
    pause
    exit /b 1
)

if not exist "main.py" (
    echo Nie znaleziono pliku main.py w:
    echo %APP_DIR%
    pause
    exit /b 1
)

start "" "%PYTHONW%" "%APP_DIR%\main.py"
exit /b 0