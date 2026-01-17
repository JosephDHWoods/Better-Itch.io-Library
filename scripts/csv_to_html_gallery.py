import time
import os
import sys
import subprocess
from playwright.sync_api import sync_playwright

# Import the other scripts directly so the EXE can find them!
from scripts import itch_scraper
from scripts import csv_to_html_gallery

# Check if we are running as a compiled EXE (frozen) or a normal script
if getattr(sys, 'frozen', False):
    # We are an EXE! Use the folder where the EXE is located.
    ROOT_DIR = os.path.dirname(sys.executable)
else:
    # We are a script! Use the folder where this file is located.
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) 
    ROOT_DIR   = os.path.dirname(SCRIPT_DIR)

DATA_DIR       = os.path.join(ROOT_DIR, "data")
html_filename  = "My purchases - itch.io.htm"
html_path      = os.path.join(DATA_DIR, html_filename)
user_data_path = os.path.join(DATA_DIR, "itch_user_data")

def fetch_itch_library(gui_confirmation=None):
    print("Starting browser automation...")
    
    # Ensure data folder exists in the REAL root (not temp)
    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR)
            print(f"Created data folder at: {DATA_DIR}")
        except Exception as e:
            print(f"Error creating data folder: {e}")

    with sync_playwright() as p:
        print("1. Opening Browser...")
        # We use a persistent context so we don't have to log in every time
        context = p.chromium.launch_persistent_context(
            user_data_path,
            headless=False,
            channel="chrome", 
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        
        page = context.pages[0] if context.pages else context.new_page()

        print("2. Going to Itch.io... \n(NOTE: First run might skip to saving. If so, click NO and rerun.)")
        page.goto("https://itch.io/my-purchases")

        print("   Waiting for the list to load...")
        try:
            page.wait_for_selector(".game_grid_widget", timeout=30000)
            print("   -> Loaded!")
        except:
            print("   (Note: Couldn't find the game grid. Make sure you're logged in.)")

        print("\n3. Scrolling down...")
        
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
            print("Did it scroll to the bottom?")
            input("Press Enter to save...") 

        if save_file:
            print("4. Saving HTML file...")
            content = page.content()
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Success! Saved to: {html_filename}")
            
            # Run the next steps automatically
            run_scraper_conversion()
            generate_gallery()
            
        else:
            print("Cancelled by user.")
            
        context.close()

def run_scraper_conversion():
    print("\n5. Running Scraper (HTML -> CSV)...")
    try:
        # Calling the function directly 
        itch_scraper.run_scraper()
        print("CSV conversion done.")
    except Exception as e:
        print(f"Error running scraper: {e}")

def generate_gallery():
    print("\n6. Building Gallery (CSV -> HTML)...")
    try:
        # Calling the function directly
        csv_to_html_gallery.main()
        print("\nAll done! You can open 'itch_catalog.html' now.")
    except Exception as e:
        print(f"Error generating gallery: {e}")

if __name__ == "__main__":
    fetch_itch_library()
