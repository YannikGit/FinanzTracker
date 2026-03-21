import os
import shutil
from core.storage import add_transactions, get_input_dir, get_processed_dir
from core.parsers.comdirect import ComdirectParser
from core.parsers.ing import INGParser

PARSERS = {
    "comdirect": ComdirectParser(),
    "ing": INGParser()
}

def get_pending_pdfs():
    input_dir = get_input_dir()
    os.makedirs(input_dir, exist_ok=True)
    return [
        os.path.join(input_dir, f)
        for f in os.listdir(input_dir)
        if f.endswith(".pdf")
    ]

def move_to_processed(pdf_path):
    processed_dir = get_processed_dir()
    os.makedirs(processed_dir, exist_ok=True)
    filename = os.path.basename(pdf_path)
    dest = os.path.join(processed_dir, filename)
    if os.path.exists(dest):
        import time
        base, ext = os.path.splitext(filename)
        dest = os.path.join(processed_dir, f"{base}_{int(time.time())}{ext}")
    shutil.move(pdf_path, dest)
    print(f"Moved {filename} → processed/")

def import_all_pdfs(bank="comdirect"):
    pdfs = get_pending_pdfs()
    if not pdfs:
        print("No new PDFs found in input/")
        return
    if bank not in PARSERS:
        print(f"Unknown bank: {bank}. Available: {list(PARSERS.keys())}")
        return
    parser = PARSERS[bank]
    for pdf_path in pdfs:
        print(f"\nParsing {os.path.basename(pdf_path)}...")
        transactions = parser.parse(pdf_path)
        add_transactions(transactions)
        move_to_processed(pdf_path)
    print(f"\nDone! Processed {len(pdfs)} PDF(s).")