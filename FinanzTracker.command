#!/bin/bash
cd "$(dirname "$0")"

echo "Starting FinanzTracker..."

# Check if venv exists, create if not
if [ ! -d ".venv" ]; then
    echo "First run — setting up virtual environment..."
    python3 -m venv .venv
    echo "Installing dependencies..."
    .venv/bin/pip install -r requirements.txt
    echo "Setup complete!"
fi

# Activate and run
source .venv/bin/activate
open http://localhost:8501
streamlit run app.py --server.headless true