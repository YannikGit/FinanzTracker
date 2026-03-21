def classify(amount):
    if amount > 0:
        return "Einnahme"
    elif amount == 0:
        return "?"
    else:
        return "Ausgabe"

def print_transaction(t):
        print(f"{t['store']} | {t['amount']:.2f}€ | {t['date']} | {classify(t['amount'])}")

def print_all_transactions(transactions):
     for t in transactions:
        print_transaction(t)

def calc_total(transactions):
    return sum(t["amount"] for t in transactions)

def make_id(transaction):
    return f"{transaction['date']}_{transaction['store']}_{transaction['amount']}_{transaction.get('reference', 'NOREF')}"