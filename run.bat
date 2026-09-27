@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv" (
    echo Criando ambiente virtual .venv...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -e .
) else (
    call .venv\Scripts\activate.bat
)

python -m myipcams.main %*

endlocal
