#!/usr/bin/env python3
import csv
import html
import json
from collections import defaultdict
from pathlib import Path

csv_file = Path("data/itch_purchases.csv")
collections_file = Path("data/collections.json")
output_file = Path("itch_catalog.html")

css_link = "https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css"
jquery_js = "https://code.jquery.com/jquery-3.7.1.min.js"
datatables_js = "https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"

html_header = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Itch.io Game Library</title>
  <link rel="stylesheet" href="{css_link}">
  <style>
    body {{ font-family: sans-serif; padding: 20px; background: #fefefe; transition: background-color 0.3s, color 0.3s; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
    td img {{
      transition: transform 0.2s ease, box-shadow 0.2s ease;
      transform-origin: top left;
      position: relative; z-index: 1; cursor: zoom-in;
    }}
    td img:hover {{
      transform: scale(3.5); z-index: 9999;
      box-shadow: 5px 5px 15px rgba(0,0,0,0.3); border-radius: 4px; background-color: white;
    }}
    .filter-chip {{
      display: inline-block; padding: 3px 8px; margin: 2px;
      border-radius: 12px; font-size: 0.85em; color: #222; text-decoration: none;
      border: 1px solid rgba(0,0,0,0.1); transition: transform 0.1s, filter 0.1s;
    }}
    .filter-chip:hover {{ transform: scale(1.05); filter: brightness(0.95); cursor: pointer; }}
    .rank-chip {{
      display: inline-block; padding: 2px 8px; border-radius: 12px;
      font-weight: bold; color: #444; border: 2px solid #ccc; min-width: 30px;
      text-align: center; background-color: rgba(255,255,255,0.5);
    }}
    summary.desc-toggle {{ cursor: pointer; color: #007bff; font-size: 0.85em; font-weight: bold; user-select: none; margin-top: 4px; display: inline-block; }}
    summary.desc-toggle:hover {{ text-decoration: underline; }}
    .desc-box {{
        margin-top: 6px; padding: 10px; background: #f8f9fa; border: 1px solid #e9ecef;
        border-radius: 4px; max-height: 250px; overflow-y: auto; white-space: pre-wrap; font-size: 0.9em; line-height: 1.5; color: #333; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
    }}
    #clear-filter {{ display: none; background-color: #ff4d4d; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold; margin-bottom: 10px; }}
    #clear-filter:hover {{ background-color: #cc0000; }}
    .alpha-bar {{ margin-bottom: 15px; display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }}
    .alpha-btn {{ padding: 5px 10px; background: #eee; border: 1px solid #ddd; cursor: pointer; font-size: 0.9em; border-radius: 3px; min-width: 30px; color: #333; }}
    .alpha-btn:hover {{ background: #ddd; }}
    .alpha-btn.active {{ background: #007bff; color: white; border-color: #0056b3; }}
    .page-jump-container {{ margin-right: 15px; font-size: 0.9em; color: #333; display: inline-block; }}
    .page-jump-input {{ width: 50px; padding: 2px; margin-left: 5px; text-align: center; border: 1px solid #aaa; border-radius: 3px; }}
    .toolbar-btn {{ padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold; border: none; }}
    
    /* Tag Editor Styles */
    .tag-editor-container {{
        border: 1px solid #ccc; padding: 4px; border-radius: 4px; display: flex; flex-wrap: wrap; gap: 4px; align-items: center; background: #fff; min-height: 28px;
    }}
    .tag-edit-chip {{
        background: #007bff; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.85em; display: flex; align-items: center; gap: 4px;
    }}
    .tag-edit-chip .remove-tag {{ cursor: pointer; font-weight: bold; font-size: 1.1em; line-height: 1; }}
    .tag-edit-chip .remove-tag:hover {{ color: #ffcccc; }}
    .tag-input-add {{
        border: none; outline: none; background: transparent; flex-grow: 1; min-width: 60px; font-size: 0.85em; color: inherit;
    }}
    .available-tags {{ margin-top: 4px; display: flex; flex-wrap: wrap; gap: 4px; }}
    .available-tag-chip {{
        background: #e9ecef; color: #495057; padding: 2px 8px; border-radius: 12px; font-size: 0.75em; cursor: pointer; border: 1px solid #ced4da; transition: background 0.2s;
    }}
    .available-tag-chip:hover {{ background: #dde2e6; }}
    
    /* Dark Mode Styles */
    body.dark-mode {{ background-color: #121212; color: #e0e0e0; }}
    body.dark-mode a {{ color: #4da6ff; }}
    body.dark-mode a:visited {{ color: #b388ff; }}
    body.dark-mode a:hover {{ color: #80c1ff; }}
    body.dark-mode .desc-box {{ background-color: #1e1e1e; color: #ccc; border-color: #333; }}
    body.dark-mode .alpha-btn {{ background-color: #2a2a2a; color: #ddd; border-color: #444; }}
    body.dark-mode .alpha-btn:hover {{ background-color: #3a3a3a; }}
    body.dark-mode .alpha-btn.active {{ background-color: #0056b3; color: white; border-color: #004494; }}
    body.dark-mode table.dataTable thead th, body.dark-mode table.dataTable thead td {{ border-bottom: 1px solid #444; }}
    body.dark-mode .dataTables_wrapper .dataTables_length, body.dark-mode .dataTables_wrapper .dataTables_filter, 
    body.dark-mode .dataTables_wrapper .dataTables_info, body.dark-mode .dataTables_wrapper .dataTables_processing, 
    body.dark-mode .dataTables_wrapper .dataTables_paginate {{ color: #ccc; }}
    body.dark-mode .dataTables_wrapper .dataTables_paginate .paginate_button {{ color: #ccc !important; }}
    body.dark-mode input, body.dark-mode select {{ background-color: #2a2a2a; color: #e0e0e0; border: 1px solid #444; }}
    body.dark-mode .page-jump-container {{ color: #ccc; }}
    body.dark-mode .tag-editor-container {{ background: #2a2a2a; border-color: #444; }}
    body.dark-mode .available-tag-chip {{ background: #333; color: #ccc; border-color: #555; }}
    body.dark-mode .available-tag-chip:hover {{ background: #444; }}
  </style>
</head>
<body>
<h1>Itch.io Game Library</h1>

<div class="alpha-bar" id="alpha-bar">
    <div id="alpha-buttons-container" style="display: flex; flex-wrap: wrap; gap: 4px;"></div>
    <div style="margin-left: auto; display: flex; gap: 5px; align-items: center;">
        <select id="global-del-select" style="display:none; padding: 6px; border-radius: 4px; max-width: 150px;"></select>
        <button class="toolbar-btn" id="global-del-btn" style="display:none; background:#dc3545; color:white;" title="Remove this collection from all games">🗑️ Remove</button>
        <div style="width: 10px; display:inline-block;"></div>
        <button class="toolbar-btn" id="dark-mode-btn" style="background:#343a40; color:white;">🌙 Dark Mode</button>
        <button class="toolbar-btn" id="toggle-col-btn" style="background:#007bff; color:white;">✏️ Edit Collections</button>
        <button class="toolbar-btn" id="save-col-local-btn" style="display:none; background:#28a745; color:white;">💾 Save to Browser</button>
        <button class="toolbar-btn" id="export-col-btn" style="display:none; background:#6c757d; color:white;">📦 Export JSON</button>
        <button class="toolbar-btn" id="import-col-btn" style="display:none; background:#ffc107; color:black;">📂 Import JSON</button>
        <input type="file" id="import-col-file" accept=".json" style="display:none;">
    </div>
</div>

<button id="clear-filter">Reset Filters</button>

<table id="games" class="display" style="width:100%">
  <thead>
    <tr>
      <th style="width: 100px;">Image</th> 
      <th style="width: auto;">Game Name</th>
      <th style="width: 120px;">Author</th>
      <th style="width: 85px;">Category</th>
      <th style="width: 100px;">Genre</th>
      <th style="width: 130px;">Tags</th>
      <th style="width: 60px;">Price</th>
      <th style="width: 110px;">Collections</th>
      <th style="width: 50px;" title="Lower number = Oldest Acquisition">Added</th>
    </tr>
  </thead>
  <tbody>
"""

def get_pastel_color(text): 
    if not text: return "#eee"
    hash_val = 0
    for char in text: hash_val = ord(char) + ((hash_val << 5) - hash_val)
    r = int((((hash_val >> 0) & 0xFF) + 255) / 2)
    g = int((((hash_val >> 8) & 0xFF) + 255) / 2)
    b = int((((hash_val >> 16) & 0xFF) + 255) / 2)
    return f"#{r:02x}{g:02x}{b:02x}"

RANK_COLORS = ["#FF5252", "#FF7043", "#FBC02D", "#66BB6A", "#26A69A", "#00BCD4", "#42A5F5", "#5C6BC0", "#AB47BC", "#EC407A"]

def get_digital_root(n):
    if n == 0: return 0
    while n > 9: n = sum(int(digit) for digit in str(n))
    return n

def safe_text(value):
    txt = (value or "").strip()
    return txt if txt else "N/A"

def safe_html(value):
    return html.escape(value or "", quote=True)

def make_chips(cell):
    if not cell or not cell.strip(): return "N/A"
    tags = [t.strip() for t in cell.split(",") if t.strip()]
    if not tags: return "N/A"
    links = []
    for tag in tags:
        color = get_pastel_color(tag)
        links.append(f'<a href="#" class="filter-chip" style="background-color: {color}; color: #222;">{safe_html(tag)}</a>')
    return " ".join(links)

def build_rows(path):
    groups = defaultdict(list)
    game_rank_map = {}

    col_db = {}
    if collections_file.exists():
        try:
            col_db = json.loads(collections_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    if not path.exists():
        return "<tr><td colspan='9'>Error: CSV file not found.</td></tr>"

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)
        
        current_rank = 1
        for record in reversed(all_rows):
            name = record.get("Game Name", "").strip()
            link = record.get("Game Page Link", "").strip()
            key = (name, link)
            
            if key not in game_rank_map:
                game_rank_map[key] = current_rank
                current_rank += 1
            
            groups[key].append(record)

    rows = []
    
    for (game_name, page_link), records in sorted(groups.items()):
        count = len(records)
        first = records[0]
        rank_num = game_rank_map.get((game_name, page_link), 999999)
        digit_index = get_digital_root(rank_num)
        border_col = RANK_COLORS[digit_index]

        rank_html = f'<span class="rank-chip" style="border-color: {border_col};">{rank_num}</span>'
        thumb_url = first.get("Thumbnail", "")
        img = f'<img src="{thumb_url}" loading="lazy" alt="Game Thumbnail" style="max-width:120px; height:auto; border-radius:4px;">' if thumb_url else ""

        title = safe_html(game_name or "N/A")
        suffix = f" ({count})" if count > 1 else ""
        link = safe_html(page_link or "#")
        
        description = safe_html(first.get("Description", ""))
        details_html = ""
        if description and description != "N/A":
            details_html = f'<details style="margin-top:2px;"><summary class="desc-toggle">Description</summary><div class="desc-box">{description}</div></details>'
            
        title_cell = f'<a href="{link}" target="_blank" class="game-link-ref">{title}{suffix}</a>{details_html}'

        author   = safe_html(first.get("Author", ""))
        
        raw_cat = first.get("Category", "").strip()
        if not raw_cat or raw_cat == "N/A":
            raw_cat = "Video Game"
            
        category = make_chips(raw_cat)
        genre    = make_chips(first.get("Genre", ""))
        tags     = make_chips(first.get("Tags", ""))
        price    = safe_text(first.get("Price", ""))

        col_raw = col_db.get(page_link, "")
        
        visible_cols = [c.strip() for c in col_raw.split(",") if c.strip() and c.strip() != "[Hidden]"]
        col_chips = make_chips(",".join(visible_cols))
        
        col_html = f'''
        <div class="col-display">{col_chips}</div>
        <div class="col-edit" style="display:none; margin-top:4px;">
            <label style="font-size: 0.85em; color: #dc3545; font-weight: bold; cursor: pointer;">
                <input type="checkbox" class="hide-checkbox"> 👁️ Hide Game
            </label><br>
            <div class="tag-editor-container" style="margin-top:4px;">
                <input type="text" class="tag-input-add" placeholder="+ Add...">
            </div>
            <div class="available-tags"></div>
            <input type="hidden" class="collection-input" value="{safe_html(", ".join(visible_cols))}">
        </div>
        '''

        row_html = f"""
        <tr>
          <td>{img}</td>
          <td>{title_cell}</td>
          <td>{author}</td>
          <td>{category}</td>
          <td>{genre}</td>
          <td>{tags}</td>
          <td>{price}</td>
          <td data-raw-col="{safe_html(col_raw)}">{col_html}</td>
          <td style="text-align:center;">{rank_html}</td>
        </tr>
        """.rstrip()
        rows.append(row_html)

    return "\n".join(rows)

def main():
    rows_html = build_rows(csv_file)

    html_footer = f"""
    </tbody>
  </table>
  <script src="{jquery_js}"></script>
  <script src="{datatables_js}"></script>
  <script>
  function escapeHtml(unsafe) {{
      return (unsafe || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
  }}

  function getPastelColor(text) {{
      if (!text) return "#eee";
      let hash = 0;
      for (let i = 0; i < text.length; i++) {{
          hash = text.charCodeAt(i) + ((hash << 5) - hash);
      }}
      let r = Math.floor((((hash >> 0) & 0xFF) + 255) / 2);
      let g = Math.floor((((hash >> 8) & 0xFF) + 255) / 2);
      let b = Math.floor((((hash >> 16) & 0xFF) + 255) / 2);
      const toHex = (c) => {{
          const hex = c.toString(16);
          return hex.length === 1 ? "0" + hex : hex;
      }};
      return "#" + toHex(r) + toHex(g) + toHex(b);
  }}

  $.fn.dataTable.ext.search.push(
      function( settings, data, dataIndex, rowData, counter ) {{
          let colSelect = $('#col-filter-select');
          if(colSelect.length === 0) return true; 
          
          let colFilterVal = colSelect.val();
          let rawCol = $(settings.aoData[dataIndex].nTr).find('td:eq(7)').attr('data-raw-col') || "";
          let isHidden = rawCol.includes('[Hidden]');

          if (colFilterVal === '[Hidden]') {{
              return isHidden;
          }}
          if (isHidden) {{
              return false;
          }}
          return true;
      }}
  );

  let editingCols = false;
  let uniqueCols = new Set();

  function updateGlobalDeleteDropdown() {{
      let delSelect = $('#global-del-select');
      delSelect.empty();
      delSelect.append('<option value="">-- Remove a Collection --</option>');
      Array.from(uniqueCols).sort().forEach(c => {{
          if(c !== '[Hidden]') {{
              delSelect.append(`<option value="${{escapeHtml(c)}}">${{escapeHtml(c)}}</option>`);
          }}
      }});
  }}

  $(document).ready(function(){{
    
    let isDarkMode = localStorage.getItem('itch_dark_mode') === 'true';
    if (isDarkMode) {{
        $('body').addClass('dark-mode');
        $('#dark-mode-btn').text('☀️ Light Mode');
    }}

    $('#dark-mode-btn').click(function() {{
        $('body').toggleClass('dark-mode');
        let darkActive = $('body').hasClass('dark-mode');
        localStorage.setItem('itch_dark_mode', darkActive);
        $(this).text(darkActive ? '☀️ Light Mode' : '🌙 Dark Mode');
        $('#games').DataTable().draw(false); 
    }});

    let savedData = JSON.parse(localStorage.getItem('itch_collections')) || {{}};
    
    // Extract permanent collections (prevents deletion if 0 games have them)
    if (savedData['__KNOWN_COLLECTIONS__']) {{
        savedData['__KNOWN_COLLECTIONS__'].split(',').forEach(c => {{
            let t = c.trim();
            if (t) uniqueCols.add(t);
        }});
    }}
    // Load from local storage
    let savedKnownCols = JSON.parse(localStorage.getItem('itch_known_collections')) || [];
    savedKnownCols.forEach(c => uniqueCols.add(c));

    function saveKnownCollections() {{
        let colsArr = Array.from(uniqueCols).filter(c => c !== '[Hidden]');
        localStorage.setItem('itch_known_collections', JSON.stringify(colsArr));
        updateGlobalDeleteDropdown();
        $('.col-edit:visible').each(function() {{
            renderAvailableTagsForRow(this);
        }});
    }}

    function renderAvailableTagsForRow(colEditDiv) {{
        let editor = $(colEditDiv).find('.tag-editor-container');
        let availableContainer = $(colEditDiv).find('.available-tags');
        availableContainer.empty();
        
        let currentTags = [];
        editor.find('.tag-edit-chip').each(function() {{
            currentTags.push($(this).attr('data-tag'));
        }});
        
        Array.from(uniqueCols).sort().forEach(c => {{
            if (c !== '[Hidden]' && !currentTags.includes(c)) {{
                availableContainer.append(`<span class="available-tag-chip" data-tag="${{escapeHtml(c)}}">+ ${{escapeHtml(c)}}</span>`);
            }}
        }});
    }}
    
    $('table#games tbody tr').each(function() {{
        let link = $(this).find('.game-link-ref').attr('href');
        let colRaw = savedData[link] !== undefined ? savedData[link] : ($(this).find('td:eq(7)').attr('data-raw-col') || "");
        
        let tagsArr = colRaw.split(',').map(t => t.trim()).filter(t => t !== "");
        let isHidden = tagsArr.includes('[Hidden]');
        let visibleTags = tagsArr.filter(t => t !== '[Hidden]');
        
        $(this).find('.hide-checkbox').prop('checked', isHidden);
        $(this).find('.collection-input').val(visibleTags.join(', '));
        $(this).find('td:eq(7)').attr('data-raw-col', tagsArr.join(', '));
        
        // Build View Chips
        let chipsHtml = "N/A";
        if (visibleTags.length > 0) {{
            chipsHtml = visibleTags.map(tag => {{
                return `<a href="#" class="filter-chip" style="background-color: ${{getPastelColor(tag)}}; color: #222;">${{escapeHtml(tag)}}</a>`;
            }}).join(' ');
        }}
        $(this).find('.col-display').html(chipsHtml);
        
        // Build Editor Chips
        if (visibleTags.length > 0) {{
            let editorChipsHtml = visibleTags.map(tag => {{
                return `<span class="tag-edit-chip" data-tag="${{escapeHtml(tag)}}">${{escapeHtml(tag)}} <span class="remove-tag">×</span></span>`;
            }}).join('');
            $(editorChipsHtml).insertBefore($(this).find('.tag-input-add'));
        }}

        visibleTags.forEach(c => uniqueCols.add(c));
    }});
    
    updateGlobalDeleteDropdown();

    const alphaContainer = $('#alpha-buttons-container');
    alphaContainer.append(`<button class="alpha-btn active" id="alpha-all-btn" data-regex="">All</button>`);
    alphaContainer.append(`<button class="alpha-btn" data-regex="^[^a-zA-Z0-9]">!.?</button>`);
    alphaContainer.append(`<button class="alpha-btn" data-regex="^[0-9]">0-9</button>`);
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("").forEach(l => {{
        alphaContainer.append(`<button class="alpha-btn" data-regex="^${{l}}">${{l}}</button>`);
    }});

    const table = $('#games').DataTable({{
      orderCellsTop: true,
      fixedHeader: true,
      pageLength: 25,
      stripeClasses: [],
      rowCallback: function(row,data,index) {{
        const isDark = $('body').hasClass('dark-mode');
        const bg = index % 2 === 0 ? (isDark ? '#1e1e1e' : '#ffffff') : (isDark ? '#2a2a2a' : '#f9f9f9');
        $(row).css('background-color', bg);
        if (isDark) $(row).css('color', '#e0e0e0'); else $(row).css('color', '');
      }},
      drawCallback: function() {{
          var paginate = $(this).closest('.dataTables_wrapper').find('.dataTables_paginate');
          if (paginate.length > 0 && paginate.find('.page-jump-input').length === 0) {{
             var info = this.api().page.info();
             var jumper = $('<span class="page-jump-container">Go to: <input type="number" class="page-jump-input" min="1" max="'+info.pages+'" value="'+(info.page+1)+'"></span>');
             paginate.prepend(jumper);
             jumper.find('input').on('change keyup', function(e){{
                 if (e.type === 'keyup' && e.key !== 'Enter') return;
                 var p = parseInt(this.value) - 1;
                 if (!isNaN(p) && p >= 0 && p < info.pages) table.page(p).draw('page');
             }});
          }} else {{
             var info = this.api().page.info();
             paginate.find('.page-jump-input').val(info.page + 1);
          }}

          if (editingCols) {{
              $(this.api().table().body()).find('.col-display').hide();
              $(this.api().table().body()).find('.col-edit').show();
              $(this.api().table().body()).find('.col-edit').each(function() {{
                  renderAvailableTagsForRow(this);
              }});
          }} else {{
              $(this.api().table().body()).find('.col-edit').hide();
              $(this.api().table().body()).find('.col-display').show();
          }}
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
      }},
      {{
        targets: 8,
        render: function(data,type) {{
          if (type==='sort' || type==='type') {{
             const num = data.replace(/<[^>]+>/g,'');
             return parseInt(num) || 0;
          }}
          return data;
        }}
      }}]
    }});

    $('.alpha-btn').on('click', function(){{
        $('.alpha-btn').removeClass('active');
        $(this).addClass('active');
        let regex = $(this).data('regex');
        if (regex === "") {{
            table.column(1).search('').draw();
        }} else {{
            table.column(1).search(regex, true, false).draw();
        }}
        $('#clear-filter').show();
    }});

    $('#games thead tr').clone(false).appendTo('#games thead');
    $('#games thead tr:eq(1) th').each(function(i){{
      $(this).removeClass('sorting sorting_asc sorting_desc');
      if (i === 0) {{
        $(this).html('');
      }}
      else if (i === 3) {{
        const options = ["All", "Assets", "Book", "Comic", "Other", "Physical game", "Soundtrack", "Tool", "Video Game"];
        const select = $('<select style="width:100%"></select>')
          .append(options.map(o => `<option>${{o}}</option>`).join(''))
          .on('change', function(){{
            const val = this.value === "All" ? "" : "^" + $.fn.dataTable.util.escapeRegex(this.value) + "$";
            table.column(i).search(val, true, false).draw();
            $('#clear-filter').show();
          }}).on('click', e => e.stopPropagation());
        $(this).html(select);
      }}
      else if (i === 6) {{
        $(this).html('<label><input type="checkbox" id="paid-filter"/> Paid?</label>')
               .find('label').on('click', e => e.stopPropagation());
      }}
      else if (i === 7) {{
        let optionsHtml = '<option value="All">All</option><option value="[Hidden]">👁️ Hidden Games</option>';
        Array.from(uniqueCols).sort().forEach(c => {{
            optionsHtml += `<option value="${{escapeHtml(c)}}">${{escapeHtml(c)}}</option>`;
        }});
        
        const select = $('<select id="col-filter-select" style="width:100%"></select>')
          .append(optionsHtml)
          .on('change', function(){{
            const val = (this.value === "All" || this.value === "[Hidden]") ? "" : this.value;
            table.column(i).search(val).draw();
            $('#clear-filter').show();
          }}).on('click', e => e.stopPropagation());
        $(this).html(select);
      }}
      else if (i === 8) {{
        $(this).html(''); 
      }}
      else {{
        const input = $('<input>', {{ type: 'text', placeholder: 'Search...', style: 'width:100%' }});
        $(this).html(input).find('input')
          .on('input', function() {{
            if (table.column(i).search() !== this.value) table.column(i).search(this.value).draw();
            $('#clear-filter').show();
          }}).on('click', e => e.stopPropagation());
      }}
    }});

    $('#games tbody').on('click', '.filter-chip', function(e){{
      e.preventDefault();
      const term = $(this).text().trim();
      const col  = $(this).closest('td').index();
      const inp  = $('#games thead tr:eq(1) th').eq(col).find('input, select');
      if (inp.length) {{
        inp.val(term).trigger('change');
        if(inp.is('input')) table.column(col).search(term).draw();
        $('#clear-filter').show();
      }}
    }});

    $('#games thead').on('change','#paid-filter',function(){{
      if (this.checked) table.column(6).search('^(?!N/A$).*$',true,false).draw();
      else table.column(6).search('').draw();
      $('#clear-filter').show();
    }});

    $('#clear-filter').on('click',function(){{
      $('#games thead tr:eq(1) th input[type=text]').val('');
      $('#games thead tr:eq(1) th select').val('All').trigger('change');
      $('#paid-filter').prop('checked',false).trigger('change');
      $('#alpha-all-btn').click();
      table.search('').columns().search('').draw();
      $(this).hide();
    }});

    $('#toggle-col-btn').click(function() {{
        editingCols = !editingCols;
        if(editingCols) {{
            $('.col-display').hide();
            $('.col-edit').show();
            $('#save-col-local-btn, #export-col-btn, #import-col-btn, #global-del-select, #global-del-btn').show();
            $(this).text("❌ Cancel Edit");
            $(this).css("background", "#dc3545");
            $('.col-edit:visible').each(function() {{
                renderAvailableTagsForRow(this);
            }});
        }} else {{
            $('.col-display').show();
            $('.col-edit').hide();
            $('#save-col-local-btn, #export-col-btn, #import-col-btn, #global-del-select, #global-del-btn').hide();
            $(this).text("✏️ Edit Collections");
            $(this).css("background", "#007bff");
        }}
    }});

    $('#global-del-btn').click(function() {{
        let targetCol = $('#global-del-select').val();
        if (!targetCol) return;
        
        if (confirm(`Are you sure you want to remove the collection '${{targetCol}}' from ALL games?`)) {{
            table.rows().every(function() {{
                let node = this.node();
                let container = $(node).find('.tag-editor-container');
                container.find(`.tag-edit-chip[data-tag="${{escapeHtml(targetCol)}}"]`).remove();
                updateHiddenInput(container);
            }});
            
            uniqueCols.delete(targetCol);
            saveKnownCollections(); // THIS removes it from memory completely
            alert(`Removed '${{targetCol}}'. Remember to click '💾 Save to Browser' to keep these changes.`);
        }}
    }});

    function updateHiddenInput(container) {{
        let tags = [];
        container.find('.tag-edit-chip').each(function() {{
            tags.push($(this).attr('data-tag'));
        }});
        container.siblings('.collection-input').val(tags.join(', '));
    }}

    function addTagToGame(inputElement, val) {{
        let container = $(inputElement).closest('.tag-editor-container');
        let exists = false;
        container.find('.tag-edit-chip').each(function() {{
            if ($(this).attr('data-tag').toLowerCase() === val.toLowerCase()) exists = true;
        }});
        
        if (!exists) {{
            $(`<span class="tag-edit-chip" data-tag="${{escapeHtml(val)}}">${{escapeHtml(val)}} <span class="remove-tag">×</span></span>`).insertBefore(inputElement);
            updateHiddenInput(container);
            uniqueCols.add(val);
            saveKnownCollections(); // Saves permanently and redraws chips
        }}
    }}

    function addTagFromInput(inputElement) {{
        let val = $(inputElement).val().trim().replace(/,/g, '');
        if (val) {{
            addTagToGame(inputElement, val);
            $(inputElement).val('');
        }}
    }}

    // When clicking a suggested tag, add it
    $('#games tbody').on('click', '.available-tag-chip', function() {{
        let tag = $(this).attr('data-tag');
        let inputElement = $(this).closest('.col-edit').find('.tag-input-add');
        addTagToGame(inputElement, tag);
    }});

    // When clicking 'x' to remove a tag, move it back to suggestions
    $('#games tbody').on('click', '.remove-tag', function() {{
        let container = $(this).closest('.tag-editor-container');
        let colEdit = $(this).closest('.col-edit');
        $(this).closest('.tag-edit-chip').remove();
        updateHiddenInput(container);
        renderAvailableTagsForRow(colEdit);
    }});

    $('#games tbody').on('keydown', '.tag-input-add', function(e) {{
        if (e.key === 'Enter' || e.key === ',') {{
            e.preventDefault();
            addTagFromInput(this);
        }}
    }});

    $('#games tbody').on('blur', '.tag-input-add', function() {{
        addTagFromInput(this);
    }});

    function harvestCollectionData() {{
        let colData = JSON.parse(localStorage.getItem('itch_collections')) || {{}};
        table.rows().every(function() {{
            let node = this.node();
            let link = $(node).find('.game-link-ref').attr('href');
            let isHidden = $(node).find('.hide-checkbox').is(':checked');
            let colInput = $(node).find('.collection-input').val().trim();
            
            let finalTags = [];
            if (isHidden) finalTags.push('[Hidden]');
            if (colInput !== "") {{
                let inputTags = colInput.split(',').map(t=>t.trim()).filter(t=>t!=="" && t!=="[Hidden]");
                finalTags.push(...inputTags);
            }}
            colData[link] = finalTags.join(', ');
        }});
        
        // Save known collections to ensure empty collections survive JSON exports
        colData['__KNOWN_COLLECTIONS__'] = Array.from(uniqueCols).filter(c => c !== '[Hidden]').join(',');
        
        return colData;
    }}

    $('#save-col-local-btn').click(function() {{
        let currentSearch = table.search();
        table.search('').draw(false);
        let colData = harvestCollectionData();
        table.search(currentSearch).draw(false);
        
        localStorage.setItem('itch_collections', JSON.stringify(colData));
        location.reload(); 
    }});
    
    $('#export-col-btn').click(function() {{
        let currentSearch = table.search();
        table.search('').draw(false);
        let colData = harvestCollectionData();
        table.search(currentSearch).draw(false);

        localStorage.setItem('itch_collections', JSON.stringify(colData));

        let dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(colData, null, 4));
        let dlAnchorElem = document.createElement('a');
        dlAnchorElem.setAttribute("href", dataStr);
        dlAnchorElem.setAttribute("download", "collections.json");
        document.body.appendChild(dlAnchorElem);
        dlAnchorElem.click();
        document.body.removeChild(dlAnchorElem);
        
        setTimeout(() => location.reload(), 500);
    }});

    $('#import-col-btn').click(function() {{
        $('#import-col-file').click();
    }});

    $('#import-col-file').change(function(e) {{
        let file = e.target.files[0];
        if (!file) return;
        let reader = new FileReader();
        reader.onload = function(evt) {{
            try {{
                let importedData = JSON.parse(evt.target.result);
                let currentData = JSON.parse(localStorage.getItem('itch_collections')) || {{}};
                Object.assign(currentData, importedData);
                localStorage.setItem('itch_collections', JSON.stringify(currentData));
                alert("Collections imported successfully! Reloading page.");
                location.reload();
            }} catch (err) {{
                alert("Error parsing JSON file. Please ensure it is a valid collections.json file.");
            }}
        }};
        reader.readAsText(file);
    }});
  }});
  </script>
</body>
</html>
"""

    full_html = html_header + rows_html + html_footer
    output_file.write_text(full_html, encoding="utf-8")
    print(f"Done! Interactive catalog written to {output_file}")

if __name__ == "__main__":
    main()