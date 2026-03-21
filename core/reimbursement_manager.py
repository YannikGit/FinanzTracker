import json
import os
from core.storage import load_transactions, save_transactions, get_profile_dir
from core.models import make_id

def get_reimbursement_rules_file():
    return os.path.join(get_profile_dir(), "reimbursement_rules.json")

def load_reimbursement_rules():
    try:
        with open(get_reimbursement_rules_file(), "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_reimbursement_rules(rules):
    path = get_reimbursement_rules_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2, ensure_ascii=False)

def add_reimbursement_rule(income_store, deductions):
    """
    Add a recurring reimbursement rule.
    income_store: str — e.g. 'JulianeLedwig'
    deductions: list of dicts — [
        {"sub_category": "Miete", "amount": 479.00},
        {"sub_category": "Strom", "amount": 30.00},
    ]
    """
    rules = load_reimbursement_rules()
    rules = [r for r in rules if r["income_store"] != income_store]
    rules.append({
        "income_store": income_store,
        "deductions": deductions,
        "active": True
    })
    save_reimbursement_rules(rules)

def delete_reimbursement_rule(income_store):
    rules = load_reimbursement_rules()
    rules = [r for r in rules if r["income_store"] != income_store]
    save_reimbursement_rules(rules)

def toggle_reimbursement_rule(income_store):
    rules = load_reimbursement_rules()
    for r in rules:
        if r["income_store"] == income_store:
            r["active"] = not r["active"]
    save_reimbursement_rules(rules)

def apply_reimbursement_rules():
    """
    Apply all active recurring reimbursement rules to transactions.
    For each income transaction from a known store, finds matching
    expense transactions by sub_category and applies deductions.
    Updates reimbursement fields on both income and expense transactions.
    """
    transactions = load_transactions()
    rules = load_reimbursement_rules()
    active_rules = [r for r in rules if r["active"]]

    if not active_rules:
        return transactions

    # Reset all rule-based reimbursements first
    # (so re-running doesn't double-apply)
    for t in transactions:
        if t.get("reimbursement_status") in ("full_rule", "partial_rule"):
            t["reimbursed_by"] = None
            t["reimbursement_amount"] = None
            t["reimbursement_status"] = None
        if t.get("reimburses") and t.get("reimbursement_source") == "rule":
            t["reimburses"] = None
            t["reimbursement_source"] = None

    for rule in active_rules:
        income_store = rule["income_store"]
        deductions = rule["deductions"]

        # Find all income transactions from this store, sorted by date
        income_transactions = sorted(
            [t for t in transactions
             if t["store"] == income_store and t["amount"] > 0],
            key=lambda t: t["date"]
        )

        for income_t in income_transactions:
            income_id = make_id(income_t)
            income_amount = income_t["amount"]
            total_deducted = 0

            for deduction in deductions:
                sub = deduction["sub_category"]
                deduct_amount = deduction["amount"]

                # Find the closest expense transaction with this sub_category
                # within 35 days of the income transaction
                from datetime import datetime, timedelta
                income_date = datetime.strptime(income_t["date"], "%d.%m.%Y")

                candidates = [
                    t for t in transactions
                    if t.get("sub_category") == sub
                    and t["amount"] < 0
                    and t.get("reimbursement_status") is None
                    and abs((datetime.strptime(t["date"], "%d.%m.%Y") - income_date).days) <= 35
                ]

                if not candidates:
                    continue

                # Pick the closest in time
                expense_t = min(
                    candidates,
                    key=lambda t: abs(
                        (datetime.strptime(t["date"], "%d.%m.%Y") - income_date).days
                    )
                )

                expense_amount = abs(expense_t["amount"])
                new_expense_amount = round(expense_amount - deduct_amount, 2)
                total_deducted += deduct_amount

                if new_expense_amount <= 0:
                    # Fully reimbursed
                    expense_t["reimbursement_amount"] = 0.0
                    expense_t["reimbursement_status"] = "full_rule"
                    expense_t["reimbursed_by"] = income_id
                else:
                    # Partially reimbursed
                    expense_t["reimbursement_amount"] = new_expense_amount
                    expense_t["reimbursement_status"] = "partial_rule"
                    expense_t["reimbursed_by"] = income_id

            # Mark the income transaction
            remaining_income = round(income_amount - total_deducted, 2)
            if remaining_income <= 0:
                income_t["reimbursement_status"] = "full_rule"
                income_t["reimburses"] = "multiple"
                income_t["reimbursement_source"] = "rule"
            else:
                income_t["reimbursement_status"] = "partial_rule"
                income_t["reimburses"] = "multiple"
                income_t["reimbursement_source"] = "rule"

    save_transactions(transactions)
    return transactions

def link_one_off_reimbursement(income_transaction_id, expense_transaction_id, reimbursement_amount):
    """
    Manually link a one-off income transaction to an expense transaction.
    """
    transactions = load_transactions()

    income_t = next((t for t in transactions if make_id(t) == income_transaction_id), None)
    expense_t = next((t for t in transactions if make_id(t) == expense_transaction_id), None)

    if not income_t or not expense_t:
        return False, "Transaction not found"

    expense_amount = abs(expense_t["amount"])
    new_expense_amount = round(expense_amount - reimbursement_amount, 2)

    if new_expense_amount <= 0:
        expense_t["reimbursement_amount"] = 0.0
        expense_t["reimbursement_status"] = "full_oneoff"
        expense_t["reimbursed_by"] = income_transaction_id
    else:
        expense_t["reimbursement_amount"] = new_expense_amount
        expense_t["reimbursement_status"] = "partial_oneoff"
        expense_t["reimbursed_by"] = income_transaction_id

    income_remaining = round(income_t["amount"] - reimbursement_amount, 2)
    if income_remaining <= 0:
        income_t["reimbursement_status"] = "full_oneoff"
    else:
        income_t["reimbursement_status"] = "partial_oneoff"
    income_t["reimburses"] = expense_transaction_id
    income_t["reimbursement_source"] = "oneoff"

    save_transactions(transactions)
    return True, "Linked successfully"

def unlink_reimbursement(transaction_id):
    """Remove reimbursement link from a transaction and its counterpart."""
    transactions = load_transactions()
    t = next((t for t in transactions if make_id(t) == transaction_id), None)
    if not t:
        return

    # Find and reset counterpart
    counterpart_id = t.get("reimbursed_by") or t.get("reimburses")
    if counterpart_id:
        counterpart = next(
            (x for x in transactions if make_id(x) == counterpart_id), None
        )
        if counterpart:
            counterpart["reimbursed_by"] = None
            counterpart["reimbursement_amount"] = None
            counterpart["reimbursement_status"] = None
            counterpart["reimburses"] = None
            counterpart["reimbursement_source"] = None

    # Reset this transaction
    t["reimbursed_by"] = None
    t["reimbursement_amount"] = None
    t["reimbursement_status"] = None
    t["reimburses"] = None
    t["reimbursement_source"] = None

    save_transactions(transactions)

def get_effective_amount(transaction):
    """
    Returns the effective display amount for a transaction,
    taking reimbursements into account.
    """
    status = transaction.get("reimbursement_status")
    if status in ("full_rule", "full_oneoff"):
        return 0.0
    elif status in ("partial_rule", "partial_oneoff"):
        reimb_amount = transaction.get("reimbursement_amount")
        if reimb_amount is not None:
            # Preserve sign
            return reimb_amount if transaction["amount"] > 0 else -reimb_amount
    return transaction["amount"]