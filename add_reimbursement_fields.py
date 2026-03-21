import json
import os

# Run this once to add reimbursement fields to all existing transactions
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILES_DIR = os.path.join(BASE_DIR, "data", "profiles")

def migrate_profile(profile_name):
    transactions_file = os.path.join(PROFILES_DIR, profile_name, "transactions.json")
    
    if not os.path.exists(transactions_file):
        print(f"No transactions.json found for profile {profile_name}")
        return

    with open(transactions_file, "r", encoding="utf-8") as f:
        transactions = json.load(f)

    updated = 0
    for t in transactions:
        if "reimbursed_by" not in t:
            t["reimbursed_by"] = None
        if "reimbursement_amount" not in t:
            t["reimbursement_amount"] = None
        if "reimbursement_status" not in t:
            t["reimbursement_status"] = None
        if "reimburses" not in t:
            t["reimburses"] = None
        updated += 1

    with open(transactions_file, "w", encoding="utf-8") as f:
        json.dump(transactions, f, indent=2, ensure_ascii=False)

    print(f"✅ Updated {updated} transactions in profile '{profile_name}'")

# Run for all profiles
profiles_file = os.path.join(PROFILES_DIR, "profiles.json")
with open(profiles_file, "r") as f:
    profiles = json.load(f)

for profile in profiles:
    migrate_profile(profile)

print("\nMigration complete!")