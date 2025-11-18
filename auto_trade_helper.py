import cv2
import numpy as np
import mss
import json
import time
from PIL import Image, ImageTk
from difflib import SequenceMatcher
import easyocr
import keyboard
import tkinter as tk
from threading import Thread
import warnings

# Suppress deprecation warnings from dependencies
warnings.filterwarnings('ignore', category=DeprecationWarning)

class TradeHelper:
    def __init__(self):
        print("="*70)
        print(" "*15 + "COUNTER BLOX TRADE HELPER - OCR")
        print("="*70)
        
        print("\n Loading EasyOCR...")
        self.reader = easyocr.Reader(['en'], gpu=False)
        print("EasyOCR ready")
        
        with open('item_values_cache.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.items = data.get('items', {})
        
        print(f"\n✓ Loaded {len(self.items)} items")
        
        # get screen dim
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            self.screen_width = monitor['width']
            self.screen_height = monitor['height']
        print(f"✓ Screen: {self.screen_width}x{self.screen_height}")
        
        print("\n" + "="*70)
        print("INSTRUCTIONS:")
        print("="*70)
        print("1. Open Counter Blox trade screen")
        print("2. Press F8 to capture and analyze")
        print("3. Press 'q' to quit")
        print("="*70 + "\n")
        
        self.running = True
        self.analyzing = False
    
    def capture_screen(self):
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            screenshot = sct.grab(monitor)
            img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
            return np.array(img)
    
    def capture_region(self, x, y, w, h):
        monitor = {"top": y, "left": x, "width": w, "height": h}
        with mss.mss() as sct:
            screenshot = sct.grab(monitor)
            img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
            return np.array(img)
    
    def preprocess_for_ocr(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        kernel = np.ones((1, 1), np.uint8)
        processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        processed = cv2.morphologyEx(processed, cv2.MORPH_OPEN, kernel)
        
        return processed
    
    def extract_text(self, img):
        try:
            # rgb shts
            results = self.reader.readtext(img, detail=0, paragraph=True)
            text = ' '.join(results)
            return text.strip()
        except Exception as e:
            print(f"   OCR Error: {e}")
            return ""
    
    def find_item(self, text):
        text = text.lower().strip()
        if len(text) < 3:
            return None, 0
        
        best = None
        best_score = 0
        
        for name, data in self.items.items():
            score = SequenceMatcher(None, text, name.lower()).ratio()
            # matching
            if score > best_score and score > 0.75:
                best_score = score
                best = data
        
        return best, best_score
    
    def parse_text_for_items(self, text):
        items = []
        found_names = set()
        
        original_text = text
        
        item_chunks = []
        if 'value' in text.lower():
            import re
            parts = re.split(r'[Vv]alue[:\s]*[\d,./]+', text)
            item_chunks = [p.strip() for p in parts if len(p.strip()) > 3]
        
        if not item_chunks:
            item_chunks = [text]
        

        
        for chunk in item_chunks:
            chunk = chunk.replace('Your Offer', '').replace('Their Offer', '').replace('Offer', '')
            chunk = chunk.replace("'s", '').replace("'", '')  # Remove apostrophes
            chunk = chunk.replace('(', ' ').replace(')', ' ').replace('_', ' ')
            chunk = chunk.replace(',', '').replace('.', '').replace('"', '').replace("'", '')
            
            import re
            chunk = re.sub(r'^\d+\s*', '', chunk)
            chunk = re.sub(r'\s*\d+$', '', chunk)
            
            chunk = chunk.strip()
            
            chunk = chunk.replace('Wve', 'Web').replace('Wveb', 'Web')
            chunk = chunk.replace('Glove ', 'Gloves ')
            chunk = chunk.replace('DesertEagle', 'Desert Eagle ')
            chunk = chunk.replace('Tec9', 'Tec-9 ')
            chunk = chunk.replace('u Tec', 'Tec')
            
            chunk = re.sub(r'\s+[A-Z][a-z]+ton\S*\s*', ' ', chunk)
            chunk = re.sub(r'\s+[A-Z][a-z]+ington\S*\s*', ' ', chunk)
            
            chunk = chunk.strip()
            
            if len(chunk) < 3:
                continue
            
            print(f"         Searching in chunk: '{chunk}'")
            
            remaining_text = chunk.lower()
            chunk_items = []
            
            for attempt in range(5):
                if len(remaining_text) < 3:
                    break
                    
                best_match = None
                best_score = 0
                best_name = None
                
                sorted_items = sorted(self.items.items(), key=lambda x: len(x[0]), reverse=True)
                
                for name, data in sorted_items:
                    name_lower = name.lower()
                    if name_lower in remaining_text:
                        score = 1.0
                    else:
                        score = SequenceMatcher(None, remaining_text, name_lower).ratio()
                    
                    if score > best_score and score > 0.50:
                        best_score = score
                        best_match = data
                        best_name = name
                
                if best_match and best_name not in found_names:
                    chunk_items.append((best_match, best_name, best_score))
                    found_names.add(best_name)
                    remaining_text = remaining_text.replace(best_name.lower(), ' ', 1)
                    remaining_text = ' '.join(remaining_text.split()) 
                    
                    if best_score < 0.75:
                        print(f"      ⚠️  Low confidence match (score: {best_score:.2f})")
                else:
                    break
            
            for match_data, match_name, match_score in chunk_items:
                items.append(match_data)
        
        return items
    
    def analyze_trade_screen(self):
        print("\n" + "─"*70)
        print("CAPTURING SCREEN...")
        print("─"*70)
        
        screen = self.capture_screen()
        screen_bgr = cv2.cvtColor(screen, cv2.COLOR_RGB2BGR)
        
        cv2.imwrite('debug_screen.png', screen_bgr)
        
        h = self.screen_height
        w = self.screen_width
        
        your_region = (0, int(h*0.10), int(w*0.35), int(h*0.30))
        their_region = (0, int(h*0.43), int(w*0.35), int(h*0.30))
        
        debug_with_regions = screen_bgr.copy()
        cv2.rectangle(debug_with_regions, 
                     (your_region[0], your_region[1]),
                     (your_region[0] + your_region[2], your_region[1] + your_region[3]),
                     (0, 255, 0), 3)
        cv2.putText(debug_with_regions, "YOUR OFFER", 
                   (your_region[0], your_region[1]-10),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        cv2.rectangle(debug_with_regions, 
                     (their_region[0], their_region[1]),
                     (their_region[0] + their_region[2], their_region[1] + their_region[3]),
                     (0, 0, 255), 3)
        cv2.putText(debug_with_regions, "THEIR OFFER", 
                   (their_region[0], their_region[1]-10),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        cv2.imwrite('debug_regions.png', debug_with_regions)
        
        print("\n SCANNING YOUR OFFER...")
        your_img = self.capture_region(*your_region)
        your_text = self.extract_text(your_img)
        
        your_items = self.parse_text_for_items(your_text)
        print(f"   Found {len(your_items)} items")
        
        print("\n SCANNING THEIR OFFER...")
        their_img = self.capture_region(*their_region)
        their_text = self.extract_text(their_img)
        
        their_items = self.parse_text_for_items(their_text)
        print(f"   Found {len(their_items)} items")
        
        if not your_items and not their_items:
            print("\n Non items detected")
            return
        
        self.show_result(your_items, their_items)
        
        result_img = self.draw_overlay(screen_bgr, your_items, their_items)
        cv2.imwrite('trade_result.png', result_img)
        print("\n Result saved: trade_result.png")
        
        # overlay screen
        print(" overlay for 15 seconds...")
        self.show_overlay_window(result_img)
    
    def draw_overlay(self, img, your_items, their_items):
        overlay = img.copy()
        h, w = overlay.shape[:2]
        
        your_val = sum(i.get('base_value', 0) for i in your_items)
        their_val = sum(i.get('base_value', 0) for i in their_items)
        diff = their_val - your_val
        pct = (diff / max(your_val, 1)) * 100 if your_val > 0 else 0
        
        your_val_adj = self.calculate_adjusted_value(your_items)
        their_val_adj = self.calculate_adjusted_value(their_items)
        diff_adj = their_val_adj - your_val_adj
        pct_adj = (diff_adj / max(your_val_adj, 1)) * 100 if your_val_adj > 0 else 0
        
        panel_w = 900
        panel_h = 400
        panel_x = w - panel_w - 30
        panel_y = 30
        
        cv2.rectangle(overlay, (panel_x, panel_y), 
                     (panel_x + panel_w, panel_y + panel_h), 
                     (30, 30, 30), -1)
        cv2.rectangle(overlay, (panel_x, panel_y), 
                     (panel_x + panel_w, panel_y + panel_h), 
                     (255, 255, 255), 3)
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        y_pos = panel_y + 50
        
        cv2.putText(overlay, "TRADE ANALYSIS", (panel_x + 30, y_pos), 
                   font, 1.2, (255, 255, 255), 2)
        
        y_pos += 60
        cv2.putText(overlay, f"Your Offer:", 
                   (panel_x + 30, y_pos), font, 0.8, (200, 200, 200), 2)
        cv2.putText(overlay, f"{int(your_val):,}", 
                   (panel_x + 250, y_pos), font, 0.8, (100, 200, 255), 2)
        cv2.putText(overlay, f"Demand: {int(your_val_adj):,}", 
                   (panel_x + 550, y_pos), font, 0.7, (80, 180, 235), 2)
        cv2.putText(overlay, f"({len(your_items)} items)", 
                   (panel_x + 30, y_pos + 30), font, 0.5, (150, 150, 150), 1)
        
        y_pos += 80
        cv2.putText(overlay, f"Their Offer:", 
                   (panel_x + 30, y_pos), font, 0.8, (200, 200, 200), 2)
        cv2.putText(overlay, f"{int(their_val):,}", 
                   (panel_x + 250, y_pos), font, 0.8, (255, 200, 100), 2)
        cv2.putText(overlay, f"Demand: {int(their_val_adj):,}", 
                   (panel_x + 550, y_pos), font, 0.7, (235, 180, 80), 2)
        cv2.putText(overlay, f"({len(their_items)} items)", 
                   (panel_x + 30, y_pos + 30), font, 0.5, (150, 150, 150), 1)
        
        y_pos += 60
        cv2.line(overlay, (panel_x + 30, y_pos - 30), 
                (panel_x + panel_w - 30, y_pos - 30), (100, 100, 100), 2)
        
        if abs(diff) < 50:
            status = "FAIR TRADE"
            color = (0, 255, 255)
        elif diff > 0:
            status = f"WIN (+{int(diff):,} / +{pct:.1f}%)"
            color = (0, 255, 0)
        else:
            status = f"LOSE ({int(diff):,} / {pct:.1f}%)"
            color = (0, 0, 255)
        
        cv2.putText(overlay, "Base Value:", (panel_x + 30, y_pos + 10), 
                   font, 0.7, (200, 200, 200), 1)
        cv2.putText(overlay, status, (panel_x + 30, y_pos + 45), 
                   font, 1.0, color, 3)
        
        y_pos += 90
        if abs(diff_adj) < 50:
            status_adj = "FAIR TRADE"
            color_adj = (0, 255, 255)
        elif diff_adj > 0:
            status_adj = f"WIN (+{int(diff_adj):,} / +{pct_adj:.1f}%)"
            color_adj = (0, 255, 0)
        else:
            status_adj = f"LOSE ({int(diff_adj):,} / {pct_adj:.1f}%)"
            color_adj = (0, 0, 255)
        
        cv2.putText(overlay, "Demand Adjusted:", (panel_x + 30, y_pos), 
                   font, 0.7, (200, 200, 200), 1)
        cv2.putText(overlay, status_adj, (panel_x + 30, y_pos + 35), 
                   font, 1.0, color_adj, 3)
        
        result = cv2.addWeighted(overlay, 0.85, img, 0.15, 0)
        return result
    
    def calculate_adjusted_value(self, items):
        """Calculate value adjusted by demand"""
        total = 0
        for item in items:
            base = item.get('base_value', 0)
            demand = item.get('demand', 5)
            
            # Demand adjustment: 1-3=low (-20%), 4-7=normal (0%), 8-10=high (+20%)
            if demand <= 3:
                adjusted = base * 0.80
            elif demand >= 8:
                adjusted = base * 1.20
            else:
                adjusted = base
            
            total += adjusted
        return total
    
    def show_overlay_window(self, img_bgr):
        """Display overlay panel on screen using Tkinter"""
        try:
            h, w = img_bgr.shape[:2]
            
            panel_w = 900
            panel_h = 400
            panel_x = w - panel_w - 30
            panel_y = 30
            
            panel_img = img_bgr[panel_y:panel_y+panel_h, panel_x:panel_x+panel_w]
            
            img_rgb = cv2.cvtColor(panel_img, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img_rgb)
            
            root = tk.Tk()
            root.overrideredirect(True)
            root.attributes('-topmost', True)
            root.attributes('-transparentcolor', 'black')
            
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            x_pos = screen_width - panel_w - 30
            y_pos = 30
            
            root.geometry(f'{panel_w}x{panel_h}+{x_pos}+{y_pos}')
            root.configure(bg='black')
            
            photo = ImageTk.PhotoImage(img_pil)
            
            label = tk.Label(root, image=photo, bg='black', borderwidth=0)
            label.image = photo 
            label.pack()
            
            def close_window(event=None):
                root.destroy()
            
            root.bind('<Button-1>', close_window)
            root.bind('<Escape>', close_window)
            root.after(15000, close_window) 
            
            root.mainloop()
        except Exception as e:
            print(f"    Could not display overlay: {e}")
    
    def show_result(self, your_items, their_items):
        your_val = sum(i.get('base_value', 0) for i in your_items)
        their_val = sum(i.get('base_value', 0) for i in their_items)
        
        your_val_adj = self.calculate_adjusted_value(your_items)
        their_val_adj = self.calculate_adjusted_value(their_items)
        
        print("\n" + "="*70)
        print(" "*25 + " TRADE ANALYSIS")
        print("="*70)
        
        print(f"\n YOUR OFFER ({len(your_items)} items)")
        print("─"*70)
        if your_items:
            for i in your_items:
                val = int(i.get('base_value', 0))
                demand = i.get('demand', 5)
                demand_icon = "🔥" if demand >= 8 else "❄️" if demand <= 3 else "⚖️"
                print(f"   {i['name']:<45} {demand_icon} {val:>13,}")
        else:
            print("   (no items detected)")
        print("─"*70)
        print(f"   {'BASE TOTAL:':<50} {int(your_val):>15,}")
        print(f"   {'DEMAND ADJUSTED:':<50} {int(your_val_adj):>15,}")
        
        print(f"\n THEIR OFFER ({len(their_items)} items)")
        print("─"*70)
        if their_items:
            for i in their_items:
                val = int(i.get('base_value', 0))
                demand = i.get('demand', 5)
                demand_icon = "🔥" if demand >= 8 else "❄️" if demand <= 3 else "⚖️"
                print(f"   {i['name']:<45} {demand_icon} {val:>13,}")
        else:
            print("   (no items detected)")
        print("─"*70)
        print(f"   {'BASE TOTAL:':<50} {int(their_val):>15,}")
        print(f"   {'DEMAND ADJUSTED:':<50} {int(their_val_adj):>15,}")
        
        diff = their_val - your_val
        pct = (diff / max(your_val, 1)) * 100 if your_val > 0 else 0
        
        diff_adj = their_val_adj - your_val_adj
        pct_adj = (diff_adj / max(your_val_adj, 1)) * 100 if your_val_adj > 0 else 0
        
        print("\n" + "="*70)
        print(" "*20 + " BASE VALUE ANALYSIS")
        if abs(diff) < 50:
            print(" "*25 + "⚖️  FAIR TRADE")
        elif diff > 0:
            print(" "*20 + f"✅ WIN (+{int(diff):,} | +{pct:.1f}%)")
        else:
            print(" "*20 + f"❌ LOSE ({int(diff):,} | {pct:.1f}%)")
        
        print("\n" + "─"*70)
        print(" "*18 + "🔥 DEMAND ADJUSTED ANALYSIS")
        if abs(diff_adj) < 50:
            print(" "*25 + "⚖️  FAIR TRADE")
        elif diff_adj > 0:
            print(" "*20 + f"✅ WIN (+{int(diff_adj):,} | +{pct_adj:.1f}%)")
        else:
            print(" "*20 + f"❌ LOSE ({int(diff_adj):,} | {pct_adj:.1f}%)")
        print("="*70 + "\n")
    
    def run(self):
        print("\n Trade Helper is running!")
        print("   Press F8 anywhere to analyze trade")
        print("   Press 'q' to quit\n")
        
        def on_f8_press(e):
            if not self.analyzing:
                self.analyzing = True
                print("\n" + "="*70)
                print(" F8 pressed - Starting analysis...")
                print("="*70)
                try:
                    self.analyze_trade_screen()
                except Exception as ex:
                    print(f"\n❌ Error: {ex}")
                    import traceback
                    traceback.print_exc()
                finally:
                    self.analyzing = False
        
        def on_q_press(e):
            print("\n Exiting...")
            self.running = False
        
        keyboard.on_press_key('f8', on_f8_press)
        keyboard.on_press_key('q', on_q_press)
        
        try:
            while self.running:
                time.sleep(0.1)
        finally:
            keyboard.unhook_all()
            print(" Cleanup complete")

if __name__ == "__main__":
    try:
        print("Starting Trade Helper...")
        helper = TradeHelper()
        helper.run()
    except KeyboardInterrupt:
        print("\n\n Exiting...")
    except Exception as e:
        print(f"\n Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
