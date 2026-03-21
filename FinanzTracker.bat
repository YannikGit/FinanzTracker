@echo off
cd /d C:\Users\yagla\Documents\FinanzTracker
call venv\Scripts\activate
start http://localhost:8501
streamlit run app.py --server.headless true