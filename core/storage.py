import json
import os
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_profile_dir():
    """Get the active profile's data directory."""
    from core.profile_manager import get_active_profile, get_profile_dir
    profile = get_active_profile()
    if profile:
        return get_profile_dir(profile)
    return os.path.join(BASE_DIR, "data")  # fallback

def get_transactions_file():
    return os.path.join(get_profile_dir(), "transactions.json")

def get_categories_file():
    return os.path.join(get_profile_dir(), "categories.json")

INPUT_DIR = property(lambda self: os.path.join(get_profile_dir(), "input"))
PROCESSED_DIR = property(lambda self: os.path.join(get_profile_dir(), "processed"))

def load_transactions():
    try:
        with open(get_transactions_file(), "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        print("transactions.json is corrupted!")
        return []

def save_transactions(transactions):
    path = get_transactions_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(transactions, f, indent=2, ensure_ascii=False)

def add_transactions(new_transactions):
    existing = load_transactions()
    from core.models import make_id
    existing_ids = {make_id(t) for t in existing}
    duplicates = 0
    added = 0
    for t in new_transactions:
        if make_id(t) not in existing_ids:
            existing.append(t)
            existing_ids.add(make_id(t))
            added += 1
        else:
            duplicates += 1
    save_transactions(existing)
    print(f"Added {added} new transactions, skipped {duplicates} duplicates.")
    return existing

def get_input_dir():
    return os.path.join(get_profile_dir(), "input")

def get_processed_dir():
    return os.path.join(get_profile_dir(), "processed")