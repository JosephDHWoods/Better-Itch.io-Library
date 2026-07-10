import time
import os
import sys
import json
import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from playwright.sync_api import sync_playwright

from scripts import itch_scraper
from scripts import csv_to_html_gallery

if getattr(sys, 'frozen', False):
    ROOT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) 
    ROOT_DIR   = os.path.dirname(SCRIPT_DIR)

DATA_DIR       = os.path.join(ROOT_DIR, "data")
html_filename  = "My purchases - itch.io.htm"
html_path      = os.path.join(DATA_DIR, html_filename)
user_data_path = os.path.join(DATA_DIR, "itch_user_data")
collections_path = os.path.join(DATA_DIR, "collections.json")

def fetch_itch_library(gui_confirmation=None, auto_scroll=True, manual_wait_event=None):
    print("Starting browser automation...")
    
    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR)
            print(f"Created data folder at: {DATA_DIR}")
        except Exception as e:
            print(f"Error creating data folder: {e}")

    with sync_playwright() as p:
        print("1. Opening Browser...")
        context = p.chromium.launch_persistent_context(
            user_data_path,
            headless=False,
            channel="chrome", 
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        
        page = context.pages[0] if context.pages else context.new_page()

        print("2. Going to Itch.io...")
        page.goto("https://itch.io/my-purchases")

        print("   Waiting for the list to load...")
        try:
            page.wait_for_selector(".game_grid_widget", timeout=30000)
            print("   -> Loaded!")
        except:
            print("   (Note: Couldn't find the game grid. Make sure you're logged in.)")

        save_file = True

        if auto_scroll:
            print("\n3. Scrolling down automatically...")
            
            last_height = page.evaluate("document.body.scrollHeight")
            while True:
                page.keyboard.press("End")
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                
                new_height = page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    print("   ...height didn't change. Waiting a sec...")
                    time.sleep(3)
                    new_height = page.evaluate("document.body.scrollHeight")
                    if new_height == last_height:
                        print("   -> Reached the bottom!")
                        break
                
                last_height = new_height
                count = page.locator(".game_cell").count()
                print(f"   ...scrolled (Found {count} items so far)")
            
            print("\n" + "="*40)
            print("        CHECK THE BROWSER        ")
            print("="*40)
            
            if gui_confirmation:
                print("Waiting for you to click Yes/No in the window...")
                save_file = gui_confirmation()
            else:
                print("Did it scroll to the bottom?")
                input("Press Enter to save...") 
                
        else:
            print("\n3. Manual Mode Active.")
            print("   -> Open the Chromium browser window.")
            print("   -> Scroll down until all new games are loaded.")
            print("   -> Click '✔️ FINISH SCROLL' in the GUI to save.")
            
            if manual_wait_event:
                manual_wait_event.wait()
            else:
                input("Press Enter to save...")

        if save_file:
            print("\n4. Saving HTML file...")
            content = page.content()
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Success! Saved to: {html_filename}")
            
        else:
            print("Cancelled by user.")
            
        context.close()

def run_scraper_conversion():
    print("\n5. Running Scraper (HTML -> CSV)...")
    try:
        itch_scraper.run_scraper()
        print("CSV conversion done.")
    except Exception as e:
        print(f"Error running scraper: {e}")

def generate_gallery():
    print("\n6. Building Gallery (CSV -> HTML)...")
    try:
        csv_to_html_gallery.main()
        print("\nAll done! You can open 'itch_catalog.html' now.")
    except Exception as e:
        print(f"Error generating gallery: {e}")

def sync_collections_to_itch(selected_collections):
    print("\n--- Starting Collection Sync ---")
    
    if not selected_collections:
        print("No collections selected. Aborting sync.")
        return
        
    if not os.path.exists(collections_path):
        print("Error: collections.json not found in data folder. Aborting.")
        return

    try:
        with open(collections_path, "r", encoding="utf-8") as f:
            col_db = json.load(f)
    except Exception as e:
        print(f"Error reading collections.json: {e}")
        return

    if not col_db:
        print("Collections database is empty. Nothing to sync.")
        return

    collections_map = defaultdict(list)
    for game_url, collections_str in col_db.items():
        if game_url == "__KNOWN_COLLECTIONS__":
            continue
            
        tags = [c.strip() for c in collections_str.split(',')]
        for tag in tags:
            if tag and tag != "[Hidden]" and tag in selected_collections:
                collections_map[tag].append(game_url)

    if not collections_map:
        print("No valid games found for the selected collections.")
        return

    print(f"Loaded and grouped games by collection.")
    print(f"Processing all assigned games.\n")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_path,
            headless=False,
            channel="chrome", 
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        page = context.pages[0] if context.pages else context.new_page()

        for collection_name, game_urls in collections_map.items():
            print(f"\nProcessing Collection: '{collection_name}' ({len(game_urls)} games to sync)")
            
            for game_url in game_urls:
                print(f" -> Syncing game: {game_url}")
                sync_url = game_url.rstrip('/') + "/add-to-collection?source=game"
                
                try:
                    page.goto(sync_url)
                    page.wait_for_selector('form.add_form', timeout=15000)
                    time.sleep(1.5) 
                    
                    already_in_elements = page.locator('.already_in a').all_text_contents()
                    already_in_clean = [name.strip() for name in already_in_elements]
                    
                    if collection_name in already_in_clean:
                        print(f"    [Skipped] Already in collection '{collection_name}'")
                        continue
                    
                    raw_options = page.locator('select[name="collection[id]"] option').all_text_contents()
                    clean_options = [re.sub(r'\s*\(\d+\)$', '', opt).strip() for opt in raw_options]
                    
                    if collection_name in clean_options:
                        page.locator('input[value="existing"]').click()
                        time.sleep(0.5)
                        page.locator('.selectize-input').click()
                        time.sleep(0.5)
                        page.keyboard.type(collection_name)
                        time.sleep(0.5)
                        page.keyboard.press("Enter")
                    else:
                        page.locator('input[value="new"]').click()
                        time.sleep(0.5)
                        page.locator('input.collection_name_input').fill(collection_name)
                    
                    time.sleep(0.5)
                    page.locator('button.button:has-text("Add to collection")').click()
                    
                    page.wait_for_load_state("networkidle")
                    time.sleep(2) 
                    
                    print(f"    [Success]")
                
                except Exception as e:
                    print(f"    [Failed] Error during assignment: {e}")

        print("\nSync operation complete.")
        context.close()

def import_public_collection(url):
    print(f"\n--- Importing Collection from {url} ---")
    try:
        if "itch.io/c/" not in url:
            print("Error: That doesn't look like a valid itch.io collection URL.")
            return

        base_url = url.split("?")[0]
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        page_num = 1
        game_urls = []
        collection_name = "Imported Collection"

        while True:
            page_url = f"{base_url}?page={page_num}"
            resp = requests.get(page_url, headers=headers, timeout=10)
            
            if resp.status_code != 200:
                if page_num == 1:
                    print(f"Error: Could not load page (Status {resp.status_code}). Is it private or deleted?")
                    return
                break 

            soup = BeautifulSoup(resp.content, "html.parser")
            
            if page_num == 1:
                # 1. Try the meta tag (most reliable for raw HTML)
                meta_title = soup.find("meta", property="og:title")
                # 2. Fallback to the h2
                h2_title = soup.select_one(".grid_header h2")
                
                if meta_title and meta_title.get("content"):
                    # Meta tags look like "My Title - Collection by User", so we split it
                    collection_name = meta_title["content"].split(" - ")[0].strip()
                elif h2_title:
                    collection_name = h2_title.text.strip()
                    
                print(f"Found Collection: '{collection_name}'")

            cells = soup.find_all("div", class_="game_cell")
            if not cells:
                break 

            for cell in cells:
                link = cell.find("a", class_="game_link")
                if link and link.has_attr("href"):
                    g_url = link["href"].split("?")[0].rstrip("/")
                    game_urls.append(g_url)
            
            print(f"  ...scraped page {page_num} ({len(cells)} games)")
            page_num += 1

        if not game_urls:
            print("No games found. The collection might be empty or private.")
            return

        print(f"Total: {len(game_urls)} games. Updating collections.json...")

        col_db = {}
        if os.path.exists(collections_path):
            with open(collections_path, "r", encoding="utf-8") as f:
                try:
                    col_db = json.load(f)
                except json.JSONDecodeError:
                    pass

        known_str = col_db.get("__KNOWN_COLLECTIONS__", "")
        known_list = [c.strip() for c in known_str.split(",") if c.strip()]
        if collection_name not in known_list:
            known_list.append(collection_name)
        col_db["__KNOWN_COLLECTIONS__"] = ", ".join(known_list)

        added_count = 0
        for g_url in set(game_urls): 
            existing = col_db.get(g_url, "")
            tags = [t.strip() for t in existing.split(",") if t.strip()]
            if collection_name not in tags:
                tags.append(collection_name)
                col_db[g_url] = ", ".join(tags)
                added_count += 1

        with open(collections_path, "w", encoding="utf-8") as f:
            json.dump(col_db, f, indent=4)

        print(f"Success! Tagged {added_count} games with '{collection_name}'.")
        print("Rebuilding HTML gallery...")

    except Exception as e:
        print(f"Error during import: {e}")

if __name__ == "__main__":
    fetch_itch_library(auto_scroll=True)