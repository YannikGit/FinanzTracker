# 💰 FinanzTracker

A personal finance tracking app built with Python and Streamlit.

## Features
- Import bank statements (Comdirect, ING)
- Automatic transaction categorization
- Receipt scanning and linking
- Interactive charts and analysis
- Multi-profile support
- Reimbursement tracking

## Installation

### Requirements
- Python 3.10 or higher

### Windows
1. Download or clone this repository
2. Double-click `FinanzTracker.bat`
3. The app opens automatically in your browser

### Mac
1. Download or clone this repository
2. Open Terminal and run: `chmod +x FinanzTracker.command`
3. Double-click `FinanzTracker.command`
4. The app opens automatically in your browser

### Manual (any system)
```bash
git clone https://github.com/yourusername/FinanzTracker
cd FinanzTracker
python3 -m venv .venv
source .venv/bin/activate  # Mac/Linux
# OR
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
streamlit run app.py
```

## Supported Banks
- Comdirect
- ING-DiBa

## Adding your data
Drop your bank PDFs into the Import tab and follow the instructions.