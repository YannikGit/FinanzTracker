@echo off
cd /d "%~dp0"

echo Starting FinanzTracker...

REM Check if venv exists, create if not
if not exist ".venv" (
    echo First run — setting up virtual environment...
    python -m venv .venv
    echo Installing dependencies...
    .venv\Scripts\pip install -r requirements.txt
    echo Setup complete!
)

REM Activate and run
call .venv\Scripts\activate
start http://localhost:8501
streamlit run app.py --server.headless true