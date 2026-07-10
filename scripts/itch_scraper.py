import csv
import time
import os
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- OPTIMIZATION: SAFE FASTEST SESSION ---
def create_safe_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    return session

session = create_safe_session()

def get_extra_details(game_name, url):
    data = {
        "Category": "", "Genre": "", "Tags": "", 
        "Price": "N/A", "Description": ""
    }
    try:
        response = session.get(url, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")

        panel = soup.find("div", class_="game_info_panel_widget")
        if panel:
            for row in panel.find_all("tr"):
                header = row.find("td")
                if not header: continue
                txt = header.text.strip().lower()
                val = header.find_next_sibling("td")
                if "category" in txt: data["Category"] = val.get_text(separator=", ").strip()
                elif "genre" in txt: data["Genre"] = val.get_text(separator=", ").strip()
                elif "tags" in txt:
                    tags = [t.text.strip() for t in val.find_all("a")]
                    data["Tags"] = ", ".join(tags)

        price_elem = soup.select_one('.buy_row span.dollars.original_price') or soup.select_one('.buy_row span.dollars[itemprop="price"]')
        if price_elem: data["Price"] = price_elem.text.strip()
        else:
            btn = soup.select_one('a.buy_button, button.buy')
            if btn: data["Price"] = btn.get_text(strip=True)
        data["Price"] = data["Price"].replace('\n', ' ').strip()

        desc = soup.find("div", class_="formatted_description user_formatted")
        if desc: data["Description"] = desc.get_text(separator="\n", strip=True)

    except Exception as e:
        print(f"   Note: Couldn't get details for '{game_name}' ({e})")
    
    time.sleep(0.1) 
    return data

def run_scraper():
    input_html = "data/My purchases - itch.io.htm"
    output_csv = "data/itch_purchases.csv"

    # Define standard headers including the new SGDB columns
    fieldnames = [
        "Thumbnail", "Game Name", "Author", "Game Page Link", 
        "Category", "Genre", "Tags", "Price", "Description",
        "SGDB_Exists", "Art_Grid", "Art_Banner", "Art_Hero", "Art_Icon", "Art_Logo"
    ]

    old_games = []
    old_games_set = set() 
    
    # Existing data loader that handles header migration
    if os.path.exists(output_csv):
        print(f"Found existing library file: {output_csv}")
        try:
            with open(output_csv, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                old_games = list(reader)
                
                # Normalize old rows and build the validation set
                for row in old_games:
                    for field in fieldnames:
                        if field not in row:
                            row[field] = "0"
                    
                    old_games_set.add((row["Game Name"], row["Game Page Link"]))
                    
        except Exception as e:
            print(f"   Couldn't read/migrate old file ({e}), rescan recommended.")
            old_games = []
            old_games_set = set()

    if not os.path.exists(input_html):
        print(f"Error: Can't find '{input_html}'.")
        return

    with open(input_html, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    thumbs = soup.find_all("div", class_="game_thumb")
    print(f"Found {len(thumbs)} games in HTML.")

    new_games = []
    consecutive_existing = 0 

    for i, block in enumerate(thumbs, start=1):
        img_tag = block.find("img")
        thumb_url = img_tag.get("data-lazy_src", img_tag.get("src", "")) if img_tag else ""

        data_div = block.find_next_sibling("div", class_="game_cell_data")
        if not data_div: continue

        title_link = data_div.find("a", class_="title game_link")
        name = title_link.text.strip() if title_link else "Unknown"
        
        raw_url = title_link["href"] if title_link else ""
        page_url = raw_url.split("/download/")[0] if "/download/" in raw_url else raw_url

        author_div = data_div.find("div", class_="game_author")
        author = author_div.find("a").text.strip() if author_div and author_div.find("a") else "Unknown"

        # Check if the game is already in our CSV data
        if (name, page_url) in old_games_set:
            consecutive_existing += 1
            if consecutive_existing >= 3:
                print(f"Found sync point at '{name}' (3 consecutive existing games). Stopping early.")
                break
            continue
        else:
            consecutive_existing = 0

        # Basic row dict
        current_row = {
            "Thumbnail": thumb_url, "Game Name": name, "Author": author, "Game Page Link": page_url,
            "Category": "", "Genre": "", "Tags": "", "Price": "", "Description": "",
            "SGDB_Exists": "0", "Art_Grid": "0", "Art_Banner": "0", 
            "Art_Hero": "0", "Art_Icon": "0", "Art_Logo": "0"
        }

        safe_print_name = name.encode('ascii', 'replace').decode()
        print(f"[{i}/{len(thumbs)}] Processing: {safe_print_name}")
        
        details = get_extra_details(name, page_url)
        current_row.update(details)
        new_games.append(current_row)

    # Append the old data behind the newly scraped games
    final_list = new_games + old_games
    print(f"Scan complete. Total: {len(final_list)}")

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final_list)

    print(f"Saved to '{output_csv}'")

if __name__ == "__main__":
    run_scraper()