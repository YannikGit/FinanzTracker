import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Global category tree — shared across all profiles
CATEGORY_TREE_FILE = os.path.join(BASE_DIR, "data", "category_tree.json")

def get_categories_file():
    """Per-profile categories file."""
    from core.storage import get_categories_file
    return get_categories_file()

def load_category_tree():
    try:
        with open(CATEGORY_TREE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_category_tree(tree):
    with open(CATEGORY_TREE_FILE, "w", encoding="utf-8") as f:
        json.dump(tree, f, indent=2, ensure_ascii=False)

def get_top_categories():
    return list(load_category_tree().keys())

def get_subcategories(top_category):
    tree = load_category_tree()
    return tree.get(top_category, {}).get("subcategories", [])

def add_top_category(name):
    tree = load_category_tree()
    if name not in tree:
        tree[name] = {"subcategories": []}
        save_category_tree(tree)
        print(f"Added top category: {name}")

def add_subcategory(top_category, subcategory):
    tree = load_category_tree()
    if top_category not in tree:
        return
    if subcategory not in tree[top_category]["subcategories"]:
        tree[top_category]["subcategories"].append(subcategory)
        save_category_tree(tree)

def load_store_categories():
    try:
        with open(get_categories_file(), "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_store_categories(categories):
    path = get_categories_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(categories, f, indent=2, ensure_ascii=False)