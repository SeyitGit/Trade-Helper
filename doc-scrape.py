import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from bs4 import BeautifulSoup
import re

GOOGLE_DOCS_ID = "1teYBaOkmtAHz_4yEp1nJdOuzxhL09OSkYdAJt_gxTeo"
VALUE_CACHE_FILE = "item_values_cache.json"
VALUE_REFRESH_INTERVAL = 300

def remove_emojis(text: str) -> str:
    return ''.join(char for char in text if ord(char) < 128)

class ValueListFetcher:
    def __init__(self, cache_file: str = VALUE_CACHE_FILE):
        self.cache_file = cache_file
        self.values_cache: Dict[str, Dict] = {}
        self.last_update: Optional[datetime] = None
        self.refresh_interval = VALUE_REFRESH_INTERVAL
        self._load_cache()

    def _load_cache(self) -> None:
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.values_cache = data.get('items', {})
                last_update_str = data.get('last_update')
                if last_update_str:
                    self.last_update = datetime.fromisoformat(last_update_str)
                print(f"Loaded {len(self.values_cache)} items from cache")
        except FileNotFoundError:
            print("No cache file found, will fetch fresh data")
        except Exception as e:
            print(f"Error loading cache: {e}")

    def _save_cache(self) -> None:
        try:
            data = {
                'items': self.values_cache,
                'last_update': self.last_update.isoformat() if self.last_update else None
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print(f"Saved {len(self.values_cache)} items to cache")
        except Exception as e:
            print(f"Error saving cache: {e}")



    def _fetch_from_google_docs(self, document_id: str) -> Dict[str, Dict]:
        try:
            export_url = f"https://docs.google.com/document/d/{document_id}/export?format=html"

            print(f"Fetching data from Google Docs...")
            print(f"URL: {export_url}")
            response = requests.get(export_url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            items = {}

            tables = soup.find_all('table')
            print(f"Found {len(tables)} tables in document")

            all_elements = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'table'])

            for element_idx, element in enumerate(all_elements):
                if element.name != 'table':
                    continue

                current_category = ""
                candidates = []
                
                for j in range(max(0, element_idx - 5), element_idx):
                    prev_elem = all_elements[j]
                    if prev_elem.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        text = prev_elem.get_text().strip()
                        text = remove_emojis(text).strip()
                        
                        if not text or len(text) < 2:
                            continue
                        
                        cleaned_text = text
                        for suffix in ["'s", "'S"]:
                            if cleaned_text.endswith(suffix):
                                cleaned_text = cleaned_text[:-len(suffix)]
                                break
                        
                        if 'CKS' in cleaned_text or 'CASE KNIVES' in cleaned_text.upper():
                            for delimiter in ["CKS", " CK", " -", " (", "CASE"]:
                                if delimiter in cleaned_text:
                                    before = cleaned_text.split(delimiter)[0].strip()
                                    if before and len(before) >= 2:
                                        cleaned_text = before
                                        break
                        
                        cleaned_text = cleaned_text.strip()
                        
                        if cleaned_text.lower() in ['hi', 'guns', 'gloves', 'knives', '']:
                            continue
                        
                        if 'rarities' in cleaned_text.lower():
                            continue
                        
                        if 2 <= len(cleaned_text) <= 50:
                            text_lower = cleaned_text.lower()
                            
                            if cleaned_text.replace(',', '').replace('.', '').replace('-', '').replace('+', '').replace('k', '').replace(' ', '').isdigit():
                                continue
                            
                            priority = 0
                            distance = element_idx - j
                            
                            weapon_keywords = ['ak-47', 'ak', 'awp', 'm4a4', 'm4a1', 'mp', 'mac', 'p250', 'p90',
                                             'eagle', 'desert', 'deagle', 'five', 'seven', 'glock', 'usp',
                                             'famas', 'galil', 'aug', 'sg', 'ssg', 'scout', 'negev',
                                             'bizon', 'ppsh', 'thompson', 'nova', 'xm', 'mag', 'sawed',
                                             'karambit', 'huntsman', 'bayonet', 'butterfly', 'bowie',
                                             'falchion', 'flip', 'gut', 'navaja', 'shadow', 'stiletto',
                                             'talon', 'ursus', 'cleaver', 'sickle']
                            
                            has_weapon_keyword = any(kw in text_lower for kw in weapon_keywords)
                            if has_weapon_keyword:
                                priority += 100
                            
                            if any(c.isdigit() for c in cleaned_text) or '-' in cleaned_text:
                                priority += 50
                            
                            if cleaned_text.isupper() and len(cleaned_text) <= 8:
                                priority += 40
                            
                            priority += max(0, 11 - distance * 2)
                            
                            status_words = ['decent', 'good', 'bad', 'mid', 'tsthas', 'unknown yet',
                                          'null', 'doesnt exist', 'low', 'high', 'pink', 'red', 'blue',
                                          'purple', 'gold', 'covert', 'classified', 'cks', 'ck']
                            if text_lower in status_words:
                                priority -= 50
                            
                            candidates.append((priority, cleaned_text, distance))
                
                if candidates:
                    candidates.sort(key=lambda x: (-x[0], x[2]))
                    current_category = candidates[0][1]
                else:
                    current_category = "Unknown"

                print(f"\nProcessing table with category: '{current_category}'...")
                
                table = element
                rows = table.find_all('tr')

                if len(rows) < 3:
                    print(f"  Skipping - not enough rows (need at least 3, found {len(rows)})")
                    continue

                data_rows = rows[2:]

                print(f"  Found {len(data_rows)} data rows (skipped 2 header rows)")

                header_row = rows[1]
                headers = []
                for cell in header_row.find_all(['th', 'td']):
                    headers.append(cell.get_text().strip().lower())

                print(f"  Headers: {headers}")

                name_idx = 0
                base_value_idx = 1 if len(headers) > 1 else -1
                dg_value_idx = 2 if len(headers) > 2 else -1
                ck_value_idx = 3 if len(headers) > 3 else -1
                upg_value_idx = 4 if len(headers) > 4 else -1
                status_idx = 5 if len(headers) > 5 else -1

                print(f"  Column mapping: Name={name_idx}, Base={base_value_idx}, DG={dg_value_idx}, CK={ck_value_idx}, UPG={upg_value_idx}, Status={status_idx}")

                items_in_table = 0
                for row in data_rows:
                    cells = row.find_all(['td', 'th'])

                    if len(cells) <= name_idx:
                        continue

                    skin_name = cells[name_idx].get_text().strip()
                    skin_name = remove_emojis(skin_name).strip()

                    if not skin_name:
                        continue

                    skin_name_lower = skin_name.lower()

                    header_keywords = [
                        'skin', 'item', 'name', 'rarities', 'rarity',
                        'too small to have a status', 'tsthas',
                        'easy to find', 'a little bit harder to find', 'hard to find',
                        'doesn\'t exist', 'noone ever had it', 'case item',
                        'base value', 'dg value', 'ck value', 'upg value', 'status',
                        'value', 'demand', 'except mods'
                    ]

                    if any(keyword == skin_name_lower or keyword in skin_name_lower for keyword in header_keywords):
                        continue

                    status_keywords = ['good', 'bad', 'mid', 'low', 'high', 'pink', 'red', 'purple',
                                      'blue', 'gold', 'covert', 'classified', 'restricted', 'mil-spec',
                                      'consumer', 'industrial', 'decent']

                    if len(skin_name.split()) <= 2:
                        if any(keyword in skin_name_lower for keyword in status_keywords):
                            continue

                    if skin_name_lower in status_keywords:
                        continue

                    knife_keywords = ['knives', 'knife']
                    is_knife_category = any(kw in current_category.lower() for kw in knife_keywords)
                    
                    if current_category and current_category.lower() not in skin_name.lower():
                        if is_knife_category:
                            clean_category = current_category
                            for kw in [' KNIVES', ' Knives', ' knives', ' KNIFE', ' Knife', ' knife']:
                                clean_category = clean_category.replace(kw, '')
                            name = f"{clean_category} {skin_name}"
                        else:
                            name = f"{current_category} {skin_name}"
                    else:
                        name = skin_name

                    def get_numeric_value(idx):
                        if idx >= 0 and idx < len(cells):
                            text = cells[idx].get_text().strip()
                            match = re.search(r'[\d,]+\.?\d*', text.replace(',', ''))
                            if match:
                                try:
                                    return float(match.group())
                                except:
                                    return 0
                        return 0

                    def get_text_value(idx):
                        if idx >= 0 and idx < len(cells):
                            text = cells[idx].get_text().strip()
                            return remove_emojis(text).strip()
                        return ""

                    base_value = get_numeric_value(base_value_idx)
                    dg_value = get_numeric_value(dg_value_idx)
                    ck_value = get_numeric_value(ck_value_idx)
                    upg_value = get_numeric_value(upg_value_idx)
                    status = get_text_value(status_idx)

                    demand = self._status_to_demand(status)

                    primary_value = base_value or ck_value or dg_value or upg_value

                    items[name] = {
                        'name': name,
                        'value': primary_value,
                        'base_value': base_value,
                        'dg_value': dg_value,
                        'ck_value': ck_value,
                        'upg_value': upg_value,
                        'rap': primary_value,
                        'demand': demand,
                        'status': status,
                        'category': current_category
                    }
                    items_in_table += 1

                print(f"  Parsed {items_in_table} items from this table")

            print(f"\n[OK] Fetched {len(items)} items from Google Docs")
            return items

        except requests.RequestException as e:
            print(f"Error fetching from Google Docs: {e}")
            print("Make sure the document is publicly accessible or shared with 'Anyone with the link'")
            return {}
        except Exception as e:
            print(f"Unexpected error parsing Google Docs: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def _status_to_demand(self, status: str) -> int:
        status_lower = status.lower()

        if 'red' in status_lower or 'gold' in status_lower or 'covert' in status_lower:
            base = 8
        elif 'pink' in status_lower or 'classified' in status_lower:
            base = 6
        elif 'purple' in status_lower or 'restricted' in status_lower:
            base = 4
        elif 'blue' in status_lower or 'mil-spec' in status_lower:
            base = 2
        else:
            base = 5

        if 'good' in status_lower or 'high' in status_lower:
            return min(10, base + 2)
        elif 'bad' in status_lower or 'low' in status_lower:
            return max(1, base - 2)
        else:
            return base



    def should_refresh(self) -> bool:
        if not self.last_update:
            return True

        elapsed = datetime.now() - self.last_update
        return elapsed.total_seconds() > self.refresh_interval

    def fetch_values(self, force_refresh: bool = False) -> bool:
        if not force_refresh and not self.should_refresh():
            print("Cache is still fresh, skipping fetch")
            return True

        items = {}

        if GOOGLE_DOCS_ID:
            print("Fetching data from Google Docs...")
            items = self._fetch_from_google_docs(GOOGLE_DOCS_ID)

        if items:
            print(f"[OK] Loaded {len(items)} items from Google Docs")
            self.values_cache = items
            self.last_update = datetime.now()
            self._save_cache()
            return True
        else:
            print("[X] Google Docs fetch failed")
            return False

    def get_item_value(self, item_name: str) -> Optional[Dict]:
        return self.values_cache.get(item_name)

    def get_all_items(self) -> Dict[str, Dict]:
        return self.values_cache.copy()

    def get_item_names(self) -> list:
        return list(self.values_cache.keys())

    def get_cache_age(self) -> Optional[timedelta]:
        if self.last_update:
            return datetime.now() - self.last_update
        return None

def test_google_docs_fetch():
    print("=" * 60)
    print("Testing Google Docs Scraping")
    print("=" * 60)

    if not GOOGLE_DOCS_ID:
        print("\nERROR: GOOGLE_DOCS_ID not configured")
        return

    print(f"\nDocument ID: {GOOGLE_DOCS_ID}")
    print(f"URL: https://docs.google.com/document/d/{GOOGLE_DOCS_ID}")

    fetcher = ValueListFetcher()

    print("\nFetching data from Google Docs...")
    success = fetcher.fetch_values(force_refresh=True)

    if success:
        print("\n[OK] Fetch successful!")
        items = fetcher.get_all_items()
        print(f"[OK] Loaded {len(items)} items")

        print("\n" + "=" * 60)
        print("Sample Items (first 10):")
        print("=" * 60)

        for i, (name, data) in enumerate(items.items()):
            if i >= 10:
                break

            print(f"\n{i+1}. {name}")
            print(f"   Base Value: {data.get('base_value', 0)}")
            print(f"   DG Value:   {data.get('dg_value', 0)}")
            print(f"   CK Value:   {data.get('ck_value', 0)}")
            print(f"   UPG Value:  {data.get('upg_value', 0)}")
            print(f"   Status:     {data.get('status', 'N/A')}")
            print(f"   Demand:     {data.get('demand', 0)}/10")

        print("\n" + "=" * 60)
        print("Testing item lookup:")
        print("=" * 60)

        test_items = ["AK-47 Ace", "AK-47 BloodBoom", "AWP Autumness", "M4A4 Aqua Marine"]
        for item_name in test_items:
            data = fetcher.get_item_value(item_name)
            if data:
                print(f"\n[OK] Found '{item_name}':")
                print(f"  Base: {data.get('base_value')}, "
                      f"DG: {data.get('dg_value')}, "
                      f"Status: {data.get('status')}")
            else:
                print(f"\n[X] '{item_name}' not found in list")

        print("\n" + "=" * 60)
        print("Cache saved to:", VALUE_CACHE_FILE)
        print("=" * 60)

    else:
        print("\n[X] Fetch failed!")
        print("\nPossible issues:")
        print("1. Document is not publicly accessible")
        print("2. Document sharing must be set to 'Anyone with the link'")
        print("3. Internet connection issue")
        print("\nHow to fix:")
        print("1. Open your Google Doc")
        print("2. Click 'Share' button")
        print("3. Change to 'Anyone with the link' can view")
        print("4. Click 'Done'")

if __name__ == "__main__":
    test_google_docs_fetch()
