import csv
import time
import requests
from bs4 import BeautifulSoup

input_html_file = "My purchases - itch.io.htm"
output_csv_file = "itch_purchases.csv"

with open(input_html_file, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

thumb_blocks = soup.find_all("div", class_="game_thumb")
games_data = []

for i, thumb_block in enumerate(thumb_blocks, start=1):
    print(f"[{i}/{len(thumb_blocks)}] Processing game...")
    img_tag = thumb_block.find("img")
    thumbnail_url = img_tag["src"] if img_tag else ""
    game_data_block = thumb_block.find_next_sibling("div", class_="game_cell_data")
    if not game_data_block:
        continue

    title_tag = game_data_block.find("a", class_="title game_link")
    game_name = title_tag.text.strip() if title_tag else "Unknown"
    download_url = title_tag["href"] if title_tag else ""
    game_page_url = download_url.split("/download/")[0] if "/download/" in download_url else download_url
    author_tag = game_data_block.find("div", class_="game_author")
    author_link = author_tag.find("a") if author_tag else None
    game_author = author_link.text.strip() if author_link else "Unknown"
    category = ""
    genre = ""
    tags = ""
    price = "N/A"
    description = ""

    try:
        response = requests.get(game_page_url, timeout=10)
        game_soup = BeautifulSoup(response.text, "html.parser")

        info_panel = game_soup.find("div", class_="game_info_panel_widget")
        if info_panel:
            rows = info_panel.find_all("tr")
            for row in rows:
                heading = row.find("td")
                if not heading:
                    continue
                heading_text = heading.text.strip().lower()
                value_td = heading.find_next_sibling("td")

                if "category" in heading_text:
                    category = value_td.get_text(separator=", ").strip()
                elif "genre" in heading_text:
                    genre = value_td.get_text(separator=", ").strip()
                elif "tags" in heading_text:
                    tag_links = value_td.find_all("a")
                    tags = ", ".join(tag.text.strip() for tag in tag_links)

        original_price_span = game_soup.select_one('.buy_row span.dollars.original_price')
        if original_price_span:
            price = original_price_span.text.strip()
        else:
            price_span = game_soup.select_one('.buy_row span.dollars[itemprop="price"]')
            if price_span:
                price = price_span.text.strip()
            else:
                price_div = game_soup.select_one('div.game_purchase_price, div.price, .price')
                if price_div:
                    price = price_div.get_text(strip=True)
                else:
                    purchase_btn = game_soup.select_one('a.buy_button, button.buy, a.button.buy_button')
                    if purchase_btn:
                        price = purchase_btn.get_text(strip=True)
        price = price.replace('\n', ' ').strip()

        # Grab the game description
        desc_div = game_soup.find("div", class_="formatted_description user_formatted")
        if desc_div:
            description = desc_div.get_text(separator="\n", strip=True)

    except Exception as e:
        print(f"  ⚠️ Failed to fetch metadata for '{game_name}': {e}")

    games_data.append([
        thumbnail_url,
        game_name,
        game_author,
        game_page_url,
        category,
        genre,
        tags,
        price,
        description
    ])

    time.sleep(1)

with open(output_csv_file, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow([
        "Thumbnail", "Game Name", "Author",
        "Game Page Link", "Category", "Genre", "Tags", "Price", "Description"
    ])
    writer.writerows(games_data)

print(f"✅ Done! {len(games_data)} games written to '{output_csv_file}'")
