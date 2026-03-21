from core.parsers.receipts.kaufland import KauflandReceiptParser
from core.receipt_storage import (
    save_receipt,
    match_receipt_to_transaction,
    link_receipt_to_transaction,
    get_pending_receipts,
    move_receipt_to_processed
)
from core.storage import load_transactions

# Map store names to their parsers
RECEIPT_PARSERS = {
    "kaufland": KauflandReceiptParser()
}

def detect_store(pdf_path):
    """Detect which store a receipt is from based on filename or content."""
    filename = pdf_path.lower()
    for store in RECEIPT_PARSERS:
        if store in filename:
            return store
    # Default fallback — try to detect from content later
    return "kaufland"

def import_all_receipts():
    receipts = get_pending_receipts()

    if not receipts:
        print("No new receipts found in data/receipts/input/")
        return

    transactions = load_transactions()

    for pdf_path in receipts:
        print(f"\nParsing receipt: {pdf_path}")
        store = detect_store(pdf_path)
        parser = RECEIPT_PARSERS[store]

        receipt = parser.parse(pdf_path)
        save_receipt(receipt)

        match = match_receipt_to_transaction(receipt, transactions)
        if match:
            print(f"Matched: {match['store']} | {match['amount']}€ | {match['date']}")
            link_receipt_to_transaction(receipt, match, transactions)
            transactions = load_transactions()  # reload after update
        else:
            print(f"No matching transaction found for {receipt['receipt_id']}")

        move_receipt_to_processed(pdf_path)

    print(f"\nDone! Processed {len(receipts)} receipt(s).")