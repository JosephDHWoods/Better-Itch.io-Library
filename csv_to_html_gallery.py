#!/usr/bin/env python3
"""
Generate an interactive, zebra-striped Itch.io game catalog in HTML
from a CSV export, collapsing duplicates by Game Name + Game Page Link,
and appending a count in parentheses when a game appears multiple times.
"""

import csv
import html
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote

# Paths
CSV_PATH    = Path("itch_purchases.csv")
OUTPUT_PATH = Path("itch_catalog.html")

# External assets
DATATABLES_CSS = "https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css"
JQUERY_JS      = "https://code.jquery.com/jquery-3.7.1.min.js"
DATATABLES_JS  = "https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"

# HTML header (same as before)
HTML_HEADER = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Itch.io Game Library</title>
  <link rel="stylesheet" href="{DATATABLES_CSS}">
  <style>
    /* --- page & table basics --- */
    body {{ font-family: sans-serif; padding: 20px; background: #fefefe; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: auto; }}
    th, td {{ vertical-align: top; padding: 12px 10px; }}

    /* --- zebra striping override & hover --- */
    #games tbody tr:hover {{ background-color: #eef6fb !important; }}

    /* --- thumbnails & zoom --- */
    .thumb-wrapper {{ position: relative; display: inline-block; }}
    img.thumb {{
      width: 160px; height: auto; border-radius: 10px;
      object-fit: cover; box-shadow: 0 0 5px rgba(0,0,0,0.1);
      transition: transform 0.2s, box-shadow 0.2s; z-index:1;
    }}
    img.thumb:hover {{
      transform: scale(1.05); box-shadow: 0 0 8px rgba(0,0,0,0.2);
    }}
    .thumb-wrapper:hover .zoomed {{ display: block; }}
    .zoomed {{
      display: none; position: fixed; top:50%; left:50%;
      transform: translate(-50%,-50%) scale(2.25);
      z-index:1000; border:5px solid white;
      box-shadow:0 0 15px rgba(0,0,0,0.5);
      background:white; max-width:90vw; max-height:90vh;
    }}

    /* --- filter chips --- */
    .filter-chip {{
      background: #eee; padding:2px 6px; margin:2px;
      border-radius:5px; text-decoration:none; color:#333;
      font-size:0.9em; cursor:pointer;
    }}
    .filter-chip:hover {{ background:#ccc; }}

    /* --- clear button --- */
    #clear-filter {{ margin-bottom:10px; display:none; }}
  </style>
</head>
<body>
  <h1>🎮 My Itch.io Game Library</h1>
  <button id="clear-filter">Clear Filter</button>
  <table id="games" class="display">
    <thead>
      <tr>
        <th>Cover</th><th>Title</th><th>Author</th>
        <th>Category</th><th>Genre</th><th>Tags</th><th>Price</th>
      </tr>
    </thead>
    <tbody>
"""

# HTML footer with JS (same dropdown-on-Category logic)
HTML_FOOTER = f"""
    </tbody>
  </table>
  <script src="{JQUERY_JS}"></script>
  <script src="{DATATABLES_JS}"></script>
  <script>
  $(document).ready(function(){{
    const table = $('#games').DataTable({{
      orderCellsTop: true,
      fixedHeader: true,
      pageLength: 25,
      stripeClasses: [],
      rowCallback: function(row,data,index) {{
        const bg = index % 2 === 0 ? '#ffffff' : '#f9f9f9';
        $(row).css('background-color', bg);
      }},
      columnDefs: [{{
        targets: 6,
        render: function(data,type) {{
          if (type==='sort' || type==='type') {{
            const cleaned = data.replace(/<[^>]+>/g,'').replace(/[^\d.]/g,'');
            return cleaned ? parseFloat(cleaned) : Infinity;
          }}
          return data;
        }}
      }}]
    }});

    // Add filter row
    $('#games thead tr').clone(false).appendTo('#games thead');
    $('#games thead tr:eq(1) th').each(function(i){{
      $(this).removeClass('sorting sorting_asc sorting_desc');
      if (i === 0) {{
        $(this).html('');
      }}
      else if (i === 3) {{
        // Category → dropdown
        const options = [
          "All", "Assets", "Book", "Comic",
          "N/A", "Other", "Physical game",
          "Soundtrack", "Tool"
        ];
        const select = $('<select style="width:100%"></select>')
          .append(options.map(o => `<option>${{o}}</option>`).join(''))
          .on('change', function(){{
            const val = this.value === "All" ? "" : this.value;
            if (table.column(i).search() !== val) {{
              table.column(i).search(val).draw();
            }}
          }}).on('click', e => e.stopPropagation());
        $(this).html(select);
      }}
      else if (i === 6) {{
        $(this).html('<label><input type="checkbox" id="paid-filter"/> Paid?</label>')
               .find('label').on('click', e => e.stopPropagation());
      }}
      else {{
        const input = $('<input>', {{
          type: 'text', placeholder: 'Search...', style: 'width:100%'
        }});
        $(this).html(input).find('input')
          .on('keyup change', function() {{
            if (table.column(i).search() !== this.value) {{
              table.column(i).search(this.value).draw();
            }}
          }}).on('click', e => e.stopPropagation());
      }}
    }});

    // Chip click → filter
    $('#games tbody').on('click', '.filter-chip', function(e){{
      e.preventDefault();
      const term = $(this).text().trim();
      const col  = $(this).closest('td').index();
      const inp  = $('#games thead tr:eq(1) th').eq(col).find('input, select');
      if (inp.length) {{
        inp.val(term).trigger('change');
        $('#clear-filter').show();
      }}
    }});

    // Paid toggle
    $('#games thead').on('change','#paid-filter',function(){{
      if (this.checked) {{
        table.column(6).search('^(?!N/A$).*$',true,false).draw();
      }} else {{
        table.column(6).search('').draw();
      }}
      $('#clear-filter').show();
    }});

    // Clear filters
    $('#clear-filter').on('click',function(){{
      $('#games thead tr:eq(1) th input[type=text]').val('');
      $('#games thead tr:eq(1) th select').val('All');
      $('#paid-filter').prop('checked',false).trigger('change');
      table.columns().search('').draw();
      $(this).hide();
    }});
  }});
  </script>
</body>
</html>
"""

def safe_text(value: str) -> str:
    """Strip text or return 'N/A'."""
    txt = (value or "").strip()
    return txt if txt else "N/A"

def safe_html(value: str) -> str:
    """Escape for HTML."""
    return html.escape(value or "", quote=True)

def make_chips(cell: str) -> str:
    """Create clickable filter chips from comma-separated tags."""
    if not cell or not cell.strip():
        return "N/A"
    tags = [t.strip() for t in cell.split(",") if t.strip()]
    if not tags:
        return "N/A"
    return " ".join(
        f'<a href="#" class="filter-chip">{safe_html(tag)}</a>'
        for tag in tags
    )

def build_rows(csv_path: Path) -> str:
    """
    Read the CSV, group rows by (Game Name, Game Page Link),
    then emit one <tr> per group, appending ' (n)' to titles
    when count > 1.
    """
    groups = defaultdict(list)

    # 1) Read & group
    with csv_path.open(newline="", encoding="utf-8") as f:
        for record in csv.DictReader(f):
            key = (
                record.get("Game Name", "").strip(),
                record.get("Game Page Link", "").strip()
            )
            groups[key].append(record)

    rows = []
    # 2) Build one row per group
    for (game_name, page_link), records in sorted(groups.items()):
        count = len(records)
        first = records[0]  # assume metadata is identical
        # Thumbnail
        thumb_url = unquote(first.get("Thumbnail", ""))
        thumb_path = Path(thumb_url)
        if thumb_url and thumb_path.exists():
            img = (
                '<div class="thumb-wrapper">'
                f'<img class="thumb" src="{thumb_url}">'
                f'<img class="zoomed" src="{thumb_url}">'
                "</div>"
            )
        else:
            img = "N/A"

        # Title + count suffix
        title = safe_html(game_name or "N/A")
        suffix = f" ({count})" if count > 1 else ""
        link = safe_html(page_link or "#")
        description = safe_html(first.get("Description", ""))
        details_html = (
            f'<details style="margin-top:4px;"><summary style="cursor:pointer;">Description</summary>'
            f'<div style="margin-top:6px; white-space:pre-wrap; font-size:0.9em; line-height:1.4;">{description}</div></details>'
            if description != "N/A" else ""
        )
        title_cell = f'<a href="{link}" target="_blank">{title}{suffix}</a>{details_html}'

        # Other columns
        author   = safe_html(first.get("Author", ""))
        category = make_chips(first.get("Category", ""))
        genre    = make_chips(first.get("Genre", ""))
        tags     = make_chips(first.get("Tags", ""))
        price    = safe_text(first.get("Price", ""))

        row_html = f"""
        <tr>
          <td>{img}</td>
          <td>{title_cell}</td>
          <td>{author}</td>
          <td>{category}</td>
          <td>{genre}</td>
          <td>{tags}</td>
          <td>{price}</td>
        </tr>
        """.rstrip()
        rows.append(row_html)

    return "\n".join(rows)

def main():
    html_content = HTML_HEADER + build_rows(CSV_PATH) + HTML_FOOTER
    OUTPUT_PATH.write_text(html_content, encoding="utf-8")
    print(f"✅ Interactive catalog written to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
