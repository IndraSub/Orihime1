@ECHO OFF
CHCP 65001
MODE CON COLS=120
PUSHD %~dp0
TITLE INDRA Rip Tools
set PYTHON_EXEC=%cd%\binaries\windows\libraries\python.exe
if exist "%PYTHON_EXEC%" (
    "%PYTHON_EXEC%" bootstrap.py
) else (
    python bootstrap.py
)
POPD
PAUSE