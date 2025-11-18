import json

def load_items():
    try:
        with open('item_values_cache.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('items', {})
    except:
        print("Error: item_values_cache.json not found!")
        return {}

def find_item(items, search_term):
    search_lower = search_term.lower().strip()
    
    for item_name, item_data in items.items():
        if search_lower in item_name.lower():
            return item_data
    
    return None

def calculate_trade():
    items = load_items()
    print(f"\nLoaded {len(items)} items from cache\n")
    print("="*60)
    print("COUNTER BLOX TRADE HELPER")
    print("="*60)
    
    your_items = []
    their_items = []
    
    print("\nYOUR OFFER (type 'done' when finished):")
    while True:
        item_name = input("  Item name: ").strip()
        if item_name.lower() == 'done':
            break
        if not item_name:
            continue
            
        found = find_item(items, item_name)
        if found:
            your_items.append(found)
            print(f"    ✓ Added: {found['name']} - Value: {int(found.get('base_value', 0)):,}")
        else:
            print(f"    ✗ Not found. Try again.")
    
    print("\nTHEIR OFFER (type 'done' when finished):")
    while True:
        item_name = input("  Item name: ").strip()
        if item_name.lower() == 'done':
            break
        if not item_name:
            continue
            
        found = find_item(items, item_name)
        if found:
            their_items.append(found)
            print(f"    ✓ Added: {found['name']} - Value: {int(found.get('base_value', 0)):,}")
        else:
            print(f"    ✗ Not found. Try again.")
    
    your_value = sum(item.get('base_value', 0) for item in your_items)
    their_value = sum(item.get('base_value', 0) for item in their_items)
    
    print("\n" + "="*60)
    print("TRADE ANALYSIS")
    print("="*60)
    
    print(f"\nYOUR OFFER ({len(your_items)} items):")
    for item in your_items:
        value = int(item.get('base_value', 0))
        print(f"  • {item['name']:<45} {value:>10,}")
    print(f"\n{'TOTAL:':<47} {int(your_value):>10,}")
    
    print(f"\nTHEIR OFFER ({len(their_items)} items):")
    for item in their_items:
        value = int(item.get('base_value', 0))
        print(f"  • {item['name']:<45} {value:>10,}")
    print(f"\n{'TOTAL:':<47} {int(their_value):>10,}")
    
    difference = their_value - your_value
    percentage = (difference / max(your_value, 1)) * 100 if your_value > 0 else 0
    
    print("\n" + "="*60)
    if abs(difference) < 50:
        print("RESULT: FAIR TRADE")
    elif difference > 0:
        print(f"RESULT: WIN (You gain +{int(difference):,} | +{percentage:.1f}%)")
    else:
        print(f"RESULT: LOSE (You lose {int(difference):,} | {percentage:.1f}%)")
    print("="*60)
    
    print("\nWant to check another trade? (y/n): ", end="")
    if input().lower() == 'y':
        print("\n\n")
        calculate_trade()

if __name__ == "__main__":
    calculate_trade()
