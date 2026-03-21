from core.category_manager import (
    load_category_tree,
    load_store_categories,
    save_store_categories,
    add_top_category,
    add_subcategory,
    get_top_categories,
    get_subcategories
)

def ask_for_category(store, amount):
    """Interactively ask user to assign top + subcategory to a store."""
    tree = load_category_tree()
    top_categories = get_top_categories()

    print(f"\nUnknown store: {store} | {amount:.2f}€")
    print("Top categories:")
    for i, cat in enumerate(top_categories):
        print(f"  {i+1}. {cat}")
    print(f"  {len(top_categories)+1}. + Add new top category")

    # Get top category choice
    while True:
        try:
            choice = int(input("Choose top category: "))
            if 1 <= choice <= len(top_categories):
                top = top_categories[choice - 1]
                break
            elif choice == len(top_categories) + 1:
                top = input("New top category name: ").strip()
                add_top_category(top)
                break
        except ValueError:
            print("Please enter a number.")

    # Get subcategory choice
    subcategories = get_subcategories(top)
    print(f"\nSubcategories for {top}:")
    for i, sub in enumerate(subcategories):
        print(f"  {i+1}. {sub}")
    print(f"  {len(subcategories)+1}. + Add new subcategory")

    while True:
        try:
            choice = int(input("Choose subcategory: "))
            if 1 <= choice <= len(subcategories):
                sub = subcategories[choice - 1]
                break
            elif choice == len(subcategories) + 1:
                sub = input("New subcategory name: ").strip()
                add_subcategory(top, sub)
                break
        except ValueError:
            print("Please enter a number.")

    return top, sub

def categorize_transactions(transactions):
    store_categories = load_store_categories()
    updated = False

    for t in transactions:
        store = t["store"]

        # Skip if already categorized
        if t.get("top_category") is not None:
            continue

        if store in store_categories:
            # Auto-assign from memory
            t["top_category"] = store_categories[store]["top"]
            t["sub_category"] = store_categories[store]["sub"]
        else:
            # Ask user
            top, sub = ask_for_category(store, t["amount"])
            t["top_category"] = top
            t["sub_category"] = sub
            store_categories[store] = {"top": top, "sub": sub}
            updated = True

    if updated:
        save_store_categories(store_categories)

    return transactions