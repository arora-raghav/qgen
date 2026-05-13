@echo off
REM start.bat — start the QGen backend on Windows

cd /d "%~dp0"

if not exist ".venv" (
    echo Creating Python virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

pip install -q --upgrade pip
pip install -q -r requirements.txt

if not exist ".env" (
    echo Creating .env from .env.example -- please set OPENAI_API_KEY in backend\.env
    copy .env.example .env
)

echo Starting QGen backend on http://localhost:8000
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
