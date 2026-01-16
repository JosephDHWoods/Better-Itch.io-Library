import csv
import time
import os
import requests
from bs4 import BeautifulSoup

# Function to go visit the actual game page and get the extra data
# We need this because the "My Purchases" list doesn't have Tags, Genre, or Price.
# Stackoverflow said this was a "DDOS Risk" but I call it ~Easier to code~
def get_extra_details(game_name, url):
    data = {
        "Category": "",
        "Genre": "",
        "Tags": "",
        "Price": "N/A", # Default if we can't find it
        "Description": ""
    }

    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        # 1. Get the info panel (Genre, Tags, etc)
        # Itch usually puts these in a table with class 'game_info_panel_widget' but sometimes it misses tags for some reason?
        # Probably not worth fixing since it only happens on like 3 TTRPGS in my library.
        panel = soup.find("div", class_="game_info_panel_widget")
        if panel:
            for row in panel.find_all("tr"):
                header = row.find("td")
                if not header: continue
                
                txt = header.text.strip().lower()
                val = header.find_next_sibling("td")
                
                if "category" in txt:
                    data["Category"] = val.get_text(separator=", ").strip()
                elif "genre" in txt:
                    data["Genre"] = val.get_text(separator=", ").strip()
                elif "tags" in txt:
                    # Tags are usually links, so grab the text inside them
                    tags = [t.text.strip() for t in val.find_all("a")]
                    data["Tags"] = ", ".join(tags)

        # 2. Try to find the price
        # This is suck, because the layout changes depending on if it's on sale or free or also seemingly at random
        price_elem = soup.select_one('.buy_row span.dollars.original_price')
        if not price_elem:
            price_elem = soup.select_one('.buy_row span.dollars[itemprop="price"]')
        
        if price_elem:
            data["Price"] = price_elem.text.strip()
        else:
            # Fallback checks
            btn = soup.select_one('a.buy_button, button.buy')
            if btn:
                data["Price"] = btn.get_text(strip=True)

        # Clean up newlines in price
        data["Price"] = data["Price"].replace('\n', ' ').strip()

        # 3. Get the short description
        desc = soup.find("div", class_="formatted_description user_formatted")
        if desc:
            data["Description"] = desc.get_text(separator="\n", strip=True)

    except Exception as e:
        # Just log it and keep going, don't crash, if it crashes 3000 games in someone is sending me a
        # ~Pipe~Bomb~
        print(f"   Note: Couldn't get details for '{game_name}' ({e})")
    
    # Sleep for 1 second so we don't hammer the server and get blocked
    time.sleep(1) 
    # Don't be Suspicious~ Don't be Suspicious! 
    return data

# --- Main Logic ---
def run_scraper():
    # Files
    input_html = "data/My purchases - itch.io.htm"
    output_csv = "data/itch_purchases.csv"

    # 1. Check if we already have a CSV file
    # If we do, we want to grab the top 3 games to create a "Signature".
    # This lets us stop scraping once we catch up to where we left off, creating an easy "update" system
    # This also crashes if you have less than 3 games in your library.
    # But You Do NOT Need this script if you have less than 3 games, go away and buy some bundles.

    old_games = []
    signature = [] 

    if os.path.exists(output_csv):
        print(f"Found existing library file: {output_csv}")
        try:
            with open(output_csv, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                headers = next(reader, None) # Skip the header row
                if headers:
                    old_games = list(reader)
                    
                # Create a signature from the first 3 games (Name and URL)
                for row in old_games[:3]:
                    if len(row) > 3:
                        signature.append((row[1], row[3]))
                
                if signature:
                    print(f"   I'll stop when I see: {signature[0][0]}")
        except Exception as e:
            print(f"   Couldn't read the old file ({e}), so I'll rescan everything.")
            old_games = []
            signature = []

    # 2. Load the HTML file
    if not os.path.exists(input_html):
        print(f"Error: Can't find '{input_html}'. Make sure you saved the page correctly.")
        # Changed exit() to return so we don't kill the GUI
        return

    with open(input_html, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    # Find all the game boxes
    thumbs = soup.find_all("div", class_="game_thumb")
    print(f"Found {len(thumbs)} games in the HTML file.")

    new_games = []
    buffer = [] # A temp holding spot to verify matches
    sig_idx = 0 
    found_overlap = False

    # 3. Loop through the games
    for i, block in enumerate(thumbs, start=1):
        
        # Get the thumbnail (handling lazy loading attributes)
        img_tag = block.find("img")
        thumb_url = ""
        if img_tag:
            if "data-lazy_src" in img_tag.attrs:
                thumb_url = img_tag["data-lazy_src"]
            else:
                thumb_url = img_tag.get("src", "")

        # Get the text data
        data_div = block.find_next_sibling("div", class_="game_cell_data")
        if not data_div: continue

        title_link = data_div.find("a", class_="title game_link")
        name = title_link.text.strip() if title_link else "Unknown"
        
        raw_url = title_link["href"] if title_link else ""
        # Clean up the URL (remove the /download/ part if it exists)
        if "/download/" in raw_url:
            page_url = raw_url.split("/download/")[0]
        else:
            page_url = raw_url

        author_div = data_div.find("div", class_="game_author")
        author_a = author_div.find("a") if author_div else None
        author = author_a.text.strip() if author_a else "Unknown"

        # Minimal row info (before we fetch details)
        basic_row = [thumb_url, name, author, page_url]

        # --- Smart Sync Logic ---
        if signature:
            # Does this game match the current spot in our signature?
            target_name, target_link = signature[sig_idx]
            
            if name == target_name and page_url == target_link:
                # It matches~ Add to buffer, but don't fetch details yet.
                buffer.append(basic_row)
                sig_idx += 1
                
                # If we matched all 3 (or the whole signature), we are safe to stop.
                if sig_idx >= len(signature):
                    print(f"Found sync point at '{name}'! Stopping early.")
                    found_overlap = True
                    break
                continue # Skip to next game
            else: # Notice how well commented this section is person reading my code? It's because I'm stupid and kept forgetting what stuff did!
                # Mismatch. 
                if sig_idx > 0:
                    print(f"   Sync broken. Fetching details for the {len(buffer)} buffered games...")
                    
                    # We thought we had a match but didn't. 
                    # Go back and fetch details for the games we skipped.
                    for b_row in buffer:
                        print(f"   + Fetching missed: {b_row[1]}")
                        details = get_extra_details(b_row[1], b_row[3])
                        full = b_row + [details["Category"], details["Genre"], details["Tags"], details["Price"], details["Description"]]
                        new_games.append(full)
                    
                    buffer = []
                    sig_idx = 0
                    
                    # Edge case: Maybe the CURRENT game is actually the start of the signature? If this happens, idk what to do for you
                    if name == signature[0][0] and page_url == signature[0][1]:
                        buffer.append(basic_row)
                        sig_idx = 1
                        continue

        # If we get here, it's a new game.
        safe_print_name = name.encode('ascii', 'replace').decode() # Avoid crash on weeb characters
        print(f"[{i}/{len(thumbs)}] Processing: {safe_print_name}")
        
        details = get_extra_details(name, page_url)
        
        full_row = basic_row + [
            details["Category"], 
            details["Genre"], 
            details["Tags"], 
            details["Price"], 
            details["Description"]
        ]
        new_games.append(full_row)


    # 4. Save everything
    final_list = []

    if found_overlap:
        # We found the overlap, so new stuff + old stuff
        final_list = new_games + old_games
        print(f"Added {len(new_games)} new games. Total library size: {len(final_list)}")
    else:
        # We scanned to the end (or it's a fresh file)
        # Check if there's anything left in the buffer
        if buffer:
             for b_row in buffer:
                details = get_extra_details(b_row[1], b_row[3])
                full = b_row + [details["Category"], details["Genre"], details["Tags"], details["Price"], details["Description"]]
                new_games.append(full)
        
        final_list = new_games + old_games
        print(f"Scan complete. Total games: {len(final_list)}")

    # Write to CSV
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Thumbnail", "Game Name", "Author",
            "Game Page Link", "Category", "Genre", "Tags", "Price", "Description"
        ])
        writer.writerows(final_list)

    print(f"Saved to '{output_csv}'")

# Enables the script to still be run standalone if needed
if __name__ == "__main__":
    run_scraper()
