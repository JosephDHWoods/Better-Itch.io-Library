import time
import os
import sys
import subprocess
from playwright.sync_api import sync_playwright

# Import the other scripts directly so the EXE can find them!
from scripts import itch_scraper
from scripts import csv_to_html_gallery

# Settings
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) # .../scripts
ROOT_DIR   = os.path.dirname(SCRIPT_DIR)                # .../MyItchLibrary
DATA_DIR   = os.path.join(ROOT_DIR, "data")             # .../MyItchLibrary/data
html_filename  = "My purchases - itch.io.htm"
html_path      = os.path.join(DATA_DIR, html_filename)
user_data_path = os.path.join(DATA_DIR, "itch_user_data")

def fetch_itch_library(gui_confirmation=None):
    print("Starting browser automation...")
    
    with sync_playwright() as p:
        print("1. Opening Browser...")
        # We use a persistent context so we don't have to log in every time, this is less safe, BUT! also less annoying
        context = p.chromium.launch_persistent_context(
            user_data_path,
            headless=False,
            channel="chrome", # Uses actual Chrome installation because firefox didn't work
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        
        page = context.pages[0] if context.pages else context.new_page()

        print("2. Going to Itch.io... \n(NOTE!!! For some users, the first time running it will skip to trying to save after logging in)\n(If this happens just click NO and rerun the Full Update, it should work)\n(or manually scroll yourself before clicking yes, these both fix it)")
        page.goto("https://itch.io/my-purchases")

        print("   Waiting for the list to load...")
        try:
            # Wait up to 30s for the game grid to appear, could be shorter but I'm assuming some user's might have slower internet.
            page.wait_for_selector(".game_grid_widget", timeout=30000)
            print("   -> Loaded!")
        except:
            print("   (Note: Couldn't find the game grid. Make sure you're logged in.)")

        print("\n3. Scrolling down...")
        
        # Infinite scroll logic go WHEEEEEE~
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

        # Safety Check: Ask user before saving
        save_file = True
        
        print("\n" + "="*40)
        print("        CHECK THE BROWSER        ")
        print("="*40)
        
        if gui_confirmation:
            print("Waiting for you to click Yes/No in the window...")
            save_file = gui_confirmation()
        else:
            # Fallback for command line usage
            print("Did it scroll to the bottom?")
            input("Press Enter to save (or Ctrl+C to quit)...") 

        if save_file:
            print("4. Saving HTML file...")
            content = page.content()
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Success! Saved to: {html_filename}")
            run_scraper_conversion()
            generate_gallery()
        else:
            print("Cancelled by user.")
            
        context.close()

def run_scraper_conversion():
    print("\n5. Running Scraper (HTML -> CSV)...")
    try:
        # Calling the function directly instead of subprocess
        itch_scraper.run_scraper()
        print("CSV conversion done.")
    except Exception as e:
        print(f"Error running scraper: {e}")

def generate_gallery():
    print("\n6. Building Gallery (CSV -> HTML)...")
    try:
        # Calling the function directly instead of subprocess
        csv_to_html_gallery.main()
        print("\nAll done! You can open 'itch_catalog.html' now.")
    except Exception as e:
        print(f"Error generating gallery: {e}")

if __name__ == "__main__":
    fetch_itch_library()
