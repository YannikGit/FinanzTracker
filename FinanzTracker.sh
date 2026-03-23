#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "First run — setting up..."
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
fi

source .venv/bin/activate
streamlit run app.py --server.headless true