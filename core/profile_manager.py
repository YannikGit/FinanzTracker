import json
import os
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILES_DIR = os.path.join(BASE_DIR, "data", "profiles")
PROFILES_FILE = os.path.join(PROFILES_DIR, "profiles.json")
CATEGORY_TREE_FILE = os.path.join(BASE_DIR, "data", "category_tree.json")

def load_profiles():
    try:
        with open(PROFILES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_profiles(profiles):
    os.makedirs(PROFILES_DIR, exist_ok=True)
    with open(PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)

def get_profile_dir(profile_name):
    return os.path.join(PROFILES_DIR, profile_name)

def create_profile(name):
    profiles = load_profiles()
    if name in profiles:
        print(f"Profile '{name}' already exists.")
        return
    profile_dir = get_profile_dir(name)
    # Create all necessary folders
    os.makedirs(profile_dir, exist_ok=True)
    os.makedirs(os.path.join(profile_dir, "input"), exist_ok=True)
    os.makedirs(os.path.join(profile_dir, "processed"), exist_ok=True)
    os.makedirs(os.path.join(profile_dir, "receipts", "input"), exist_ok=True)
    os.makedirs(os.path.join(profile_dir, "receipts", "processed"), exist_ok=True)
    # Create empty data files
    for filename, default in [
        ("transactions.json", []),
        ("categories.json", {}),
        ("receipts.json", [])
    ]:
        filepath = os.path.join(profile_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)
    profiles.append(name)
    save_profiles(profiles)
    print(f"Profile '{name}' created.")

def delete_profile(name):
    profiles = load_profiles()
    if name not in profiles:
        print(f"Profile '{name}' not found.")
        return False
    if len(profiles) <= 1:
        print("Cannot delete the last profile.")
        return False
    # Delete profile folder and all its data
    profile_dir = get_profile_dir(name)
    if os.path.exists(profile_dir):
        shutil.rmtree(profile_dir)
    profiles.remove(name)
    save_profiles(profiles)
    print(f"Profile '{name}' deleted.")
    return True

def get_active_profile():
    try:
        active_file = os.path.join(PROFILES_DIR, "active_profile.txt")
        with open(active_file, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        profiles = load_profiles()
        if profiles:
            return profiles[0]
        return None

def set_active_profile(name):
    os.makedirs(PROFILES_DIR, exist_ok=True)
    active_file = os.path.join(PROFILES_DIR, "active_profile.txt")
    with open(active_file, "w") as f:
        f.write(name)