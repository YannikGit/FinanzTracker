import json
import os
import shutil
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_receipts_file():
    from core.storage import get_profile_dir
    return os.path.join(get_profile_dir(), "receipts.json")

def get_receipts_input_dir():
    from core.storage import get_profile_dir
    return os.path.join(get_profile_dir(), "receipts", "input")

def get_receipts_processed_dir():
    from core.storage import get_profile_dir
    return os.path.join(get_profile_dir(), "receipts", "processed")

def load_receipts():
    try:
        with open(get_receipts_file(), "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_receipt(receipt):
    receipts = load_receipts()
    existing_ids = {r["receipt_id"] for r in receipts}
    if receipt["receipt_id"] in existing_ids:
        print(f"Receipt {receipt['receipt_id']} already exists, skipping.")
        return
    receipts.append(receipt)
    path = get_receipts_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(receipts, f, indent=2)
    print(f"Saved receipt {receipt['receipt_id']}")

def match_receipt_to_transaction(receipt, transactions):
    receipt_date = datetime.strptime(receipt["date"], "%d.%m.%Y")
    receipt_total = receipt["total"]
    receipt_store = receipt["store"].upper()
    for t in transactions:
        t_date = datetime.strptime(t["date"], "%d.%m.%Y")
        t_amount = abs(t["amount"])
        t_store = t["store"].upper()
        store_match = receipt_store in t_store or t_store in receipt_store
        amount_match = abs(t_amount - receipt_total) < 0.01
        date_match = abs((t_date - receipt_date).days) <= 3
        if store_match and amount_match and date_match:
            return t
    return None

def link_receipt_to_transaction(receipt, transaction, all_transactions):
    from core.storage import save_transactions
    from core.models import make_id
    t_id = make_id(transaction)
    for t in all_transactions:
        if make_id(t) == t_id:
            t["receipt_id"] = receipt["receipt_id"]
            break
    save_transactions(all_transactions)
    receipts = load_receipts()
    for r in receipts:
        if r["receipt_id"] == receipt["receipt_id"]:
            r["transaction_ref"] = t_id
            break
    with open(get_receipts_file(), "w") as f:
        json.dump(receipts, f, indent=2)
    print(f"Linked receipt {receipt['receipt_id']} ↔ transaction {t_id}")

def get_pending_receipts():
    input_dir = get_receipts_input_dir()
    os.makedirs(input_dir, exist_ok=True)
    return [
        os.path.join(input_dir, f)
        for f in os.listdir(input_dir)
        if f.endswith(".pdf")
    ]

def move_receipt_to_processed(pdf_path):
    processed_dir = get_receipts_processed_dir()
    os.makedirs(processed_dir, exist_ok=True)
    filename = os.path.basename(pdf_path)
    dest = os.path.join(processed_dir, filename)
    if os.path.exists(dest):
        base, ext = os.path.splitext(filename)
        dest = os.path.join(processed_dir, f"{base}_{int(time.time())}{ext}")
    shutil.move(pdf_path, dest)
    print(f"Moved {filename} → receipts/processed/")