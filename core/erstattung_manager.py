import json
import os

def get_erstattung_file():
    from core.storage import get_profile_dir
    return os.path.join(get_profile_dir(), "erstattungsregeln.json")

def load_rules():
    try:
        with open(get_erstattung_file(), "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_rules(rules):
    path = get_erstattung_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2, ensure_ascii=False)

def add_rule(store, deductions):
    """
    store: str — the store/sender name e.g. 'JulianeLedwig'
    deductions: list of dicts — [
        {"subcategory": "Miete", "type": "fixed", "value": 400},
        {"subcategory": "Strom", "type": "percent", "value": 50},
    ]
    """
    rules = load_rules()
    rules = [r for r in rules if r["store"] != store]
    rules.append({
        "store": store,
        "deductions": deductions,
        "active": True
    })
    save_rules(rules)

def delete_rule(store):
    rules = load_rules()
    rules = [r for r in rules if r["store"] != store]
    save_rules(rules)

def toggle_rule(store):
    rules = load_rules()
    for r in rules:
        if r["store"] == store:
            r["active"] = not r["active"]
    save_rules(rules)

def get_latest_erstattung_amount(store, all_transactions):
    """Get the most recent transaction amount from this store."""
    store_transactions = [
        t for t in all_transactions
        if t["store"] == store and t.get("top_category") == "Einnahmen"
    ]
    if not store_transactions:
        return 0.0
    # Sort by date and get latest
    from datetime import datetime
    store_transactions.sort(
        key=lambda t: datetime.strptime(t["date"], "%d.%m.%Y"),
        reverse=True
    )
    return abs(store_transactions[0]["amount"])

def apply_rules(df, all_transactions):
    """
    Apply Erstattungsregeln and return a summary of deductions.
    For each rule, uses the latest transaction amount as the Erstattung base.
    Returns list of dicts with full breakdown and remaining amount.
    """
    rules = load_rules()
    active_rules = [r for r in rules if r["active"]]
    summaries = []

    for rule in active_rules:
        store = rule["store"]
        erstattung_amount = get_latest_erstattung_amount(store, all_transactions)

        if erstattung_amount == 0:
            continue

        # Get average monthly expense per subcategory from df
        num_months = df["date"].dt.to_period("M").nunique()
        ausgaben_df = df[df["type"] == "Ausgabe"]

        deduction_details = []
        total_deducted = 0

        for d in rule["deductions"]:
            sub = d["subcategory"]
            dtype = d["type"]  # "fixed" or "percent"
            value = d["value"]

            if dtype == "fixed":
                deducted = round(value, 2)
            else:
                # percent of the average monthly expense for this subcategory
                sub_total = abs(
                    ausgaben_df[ausgaben_df["sub_category"] == sub]["amount"].sum()
                )
                sub_avg = round(sub_total / num_months, 2)
                deducted = round(sub_avg * (value / 100), 2)

            total_deducted += deducted
            deduction_details.append({
                "subcategory": sub,
                "type": dtype,
                "value": value,
                "deducted": deducted
            })

        remaining = round(erstattung_amount - total_deducted, 2)

        summaries.append({
            "store": store,
            "erstattung_amount": erstattung_amount,
            "deductions": deduction_details,
            "total_deducted": round(total_deducted, 2),
            "remaining": remaining
        })

    return summaries