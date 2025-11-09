# export_html_full.py
import pandas as pd
import re
import os

# ========== CẤU HÌNH ==========
CSV_FILE = "iot.csv"
OUT_HTML = "dictionary1.html"
# Nếu muốn in 2 cột, set True; nếu muốn 1 cột, set False
TWO_COLUMN = False
# Title
DOC_TITLE = "TỪ ĐIỂN CHUYÊN NGÀNH OT và IoT security (English - Vietnamese)"
# ========== /CẤU HÌNH ==========

# ---- load CSV
df = pd.read_csv(CSV_FILE, encoding="utf-8", on_bad_lines="skip")
df = df.rename(columns={
    "english": "english",
    "vietnamese": "vietnamese",
    "note": "note",
    "vi_du": "example"
})
df.fillna("", inplace=True)
df = df.sort_values("english", key=lambda s: s.str.lower())

terms = df["english"].tolist()

# ---- helper: extract sub-terms that exist in database
def extract_sub_terms(text):
    found = []
    if not text:
        return found
    for t in terms:
        # match whole word, case-insensitive
        if re.search(rf"\b{re.escape(t)}\b", text, flags=re.IGNORECASE):
            if t not in found and t.strip() != "":
                found.append(t)
    return found

# ---- Build TOC grouped by initial letter
from collections import defaultdict
groups = defaultdict(list)
for t in terms:
    first = t[0].upper() if t else "#"
    if not first.isalpha():
        first = "#"
    groups[first].append(t)

sorted_letters = sorted(groups.keys(), key=lambda c: (c!="#", c))  # '#' last or first; adjust

# ---- Build content blocks
content_blocks = []
for _, row in df.iterrows():
    eng = row["english"]
    vi = row["vietnamese"]
    note = row["note"]
    ex  = row["example"]

    subs = extract_sub_terms(note)

    # Replace occurrences in note with links (only for subs that exist)
    linked_note = note
    for sub in subs:
        # use regex to replace whole-word, preserve original case
        linked_note = re.sub(
            rf"(\b){re.escape(sub)}(\b)",
            rf"\1<a href='#{sub}' class='in-link'>{sub}</a>\2",
            linked_note,
            flags=re.IGNORECASE
        )

    see_more_html = ""
    if subs:
        links = ", ".join([f"<a href='#{s}' class='in-link'>{s}</a>" for s in subs])
        see_more_html = f"<div class='see-more'><b>Xem thêm:</b> {links}</div>"

    # back-to-top link (JS/CSS will style)
    block = {
        "anchor": eng,
        "html": f"""
<a id="{eng}"></a>
<section class="term-block" data-term="{eng}">
    <div class="term">{eng}</div>

    <div class="meta"><span class="label">Dịch:</span>
        <span class="vietnamese">{vi}</span>
    </div>

    <div class="meta"><span class="label">Giải thích:</span>
        <span class="note">{linked_note}</span>
    </div>

    <div class="meta"><span class="label">Ví dụ:</span>
        <span class="example">{ex}</span>
    </div>

    {see_more_html}
    <div class="tools"><a class="back-top" href="#toc">↑ Lên đầu</a></div>
</section>
"""
    }
    content_blocks.append(block)

# ---- Build TOC HTML (clickable)
toc_entries = []
for letter in sorted_letters:
    names = groups[letter]
    # sort names alphabetically
    names = sorted(names, key=lambda s: s.lower())
    items = " · ".join([f"<a href='#{n}' class='toc-link'>{n}</a>" for n in names])
    toc_entries.append(f"<div class='toc-group'><h3>{letter}</h3><div class='toc-items'>{items}</div></div>")

toc_html = "<div id='toc' class='toc'><h2>Mục lục</h2>" + "\n".join(toc_entries) + "</div>"

# ---- final HTML template (includes paged.polyfill.js if present)
paged_js_exists = os.path.exists("paged.polyfill.js")
paged_script_tag = "<script src='paged.polyfill.js'></script>" if paged_js_exists else "<!-- paged.polyfill.js not found: download for advanced page features -->"

two_column_class = "two-column" if TWO_COLUMN else ""

html_template = f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>{DOC_TITLE}</title>
{paged_script_tag}
<style>
/* --- Basic layout --- */
:root {{
    --page-margin: 36px;
    --accent: #0060c0;
}}
body {{
    font-family: Arial, Helvetica, sans-serif;
    margin: 0;
    padding: var(--page-margin);
    color: #111;
    line-height: 1.55;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}}
header {{
    text-align: center;
    margin-bottom: 18px;
}}
h1 {{
    font-size: 30px;
    margin: 10px 0 8px;
}}
/* --- TOC --- */
.toc {{
    background: #f7fbff;
    padding: 12px;
    border-radius: 6px;
    margin-bottom: 18px;
}}
.toc h2 {{
    margin: 0 0 8px;
}}
.toc-group {{
    margin-bottom: 8px;
}}
.toc-group h3 {{
    display:inline-block;
    margin:0 10px 0 0;
    color: #333;
    font-size: 14px;
}}
.toc-items a {{
    text-decoration: none;
    color: var(--accent);
    margin-right: 6px;
    font-size: 13px;
}}
/* --- term block --- */
.term-block {{
    background: #fff;
    padding: 18px;
    border-radius: 6px;
    box-shadow: 0 0 0 1px #f0f0f0 inset;
    margin-bottom: 22px;
    page-break-inside: avoid;
}}
.term {{
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 8px;
}}
.meta {{ margin: 6px 0; }}
.label {{ font-weight:700; color:#444; margin-right:6px; }}
.vietnamese {{ color: #005fb8; }}
.note {{ color:#333; font-style: italic; }}
.example {{ color:#333; }}
.see-more {{ margin-top:8px; color: var(--accent); font-size: 14px; }}

/* link style */
a.in-link, a.toc-link, .see-more a {{
    color: var(--accent);
    text-decoration: none;
}}

/* back to top */
.tools {{ margin-top: 10px; }}
.back-top {{
    font-size: 13px;
    color: #666;
    text-decoration: none;
}}

/* highlight target */
:target {{
    outline: 3px solid rgba(0,96,192,0.15);
    background: linear-gradient(90deg, rgba(0,96,192,0.03), transparent);
    transition: background 0.35s ease;
}}

/* ========= Two-column mode (print-friendly) ========= */
.{two_column_class} .content-wrapper {{
    column-count: 2;
    column-gap: 36px;
}}

/* ensure each term-block not split across columns/pages */
.term-block {{
    break-inside: avoid-column;
}}

/* ========= Footer for page numbers (paged.js support) ========= */
@page {{
    @bottom-center {{
        content: "Trang " counter(page) " / " counter(pages);
        font-size: 12px;
        color: #666;
    }}
    margin: 36px;
}}

/* print-friendly adjustments */
@media print {{
    body {{ padding: 18mm; }}
    .term-block {{ box-shadow: none; }}
    .toc {{ background: none; }}
}}

</style>
</head>
<body class="{two_column_class}">
<header><h1>{DOC_TITLE}</h1></header>

<nav>
{toc_html}
</nav>

<main class="content-wrapper">
{"".join([b["html"] for b in content_blocks])}
</main>

<script>
// small enhancement: when clicking an internal link, scroll smoothly (works in browser)
document.querySelectorAll('a[href^="#"]').forEach(a => {{
    a.addEventListener('click', function(e) {{
        const targetId = this.getAttribute('href').slice(1);
        const el = document.getElementById(targetId) || document.querySelector('a[name="'+targetId+'"]');
        if (el) {{
            e.preventDefault();
            el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
            // update hash without default jump
            history.pushState(null, null, '#'+targetId);
        }}
    }});
}});
</script>
</body>
</html>
"""

# write output
with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html_template)

print(f"✅ Đã tạo {OUT_HTML}.")
print("Mở file bằng Chrome, Ctrl+P -> Save as PDF (chọn Background graphics).")
if not paged_js_exists:
    print("Khuyến nghị: tải paged.polyfill.js vào cùng thư mục để có hỗ trợ @page tốt hơn:")
    print("https://unpkg.com/pagedjs/dist/paged.polyfill.js")
