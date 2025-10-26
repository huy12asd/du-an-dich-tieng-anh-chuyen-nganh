from flask import Flask, request, render_template, redirect, url_for, jsonify
from googletrans import Translator
import sqlite3  # <-- THAY ĐỔI: Dùng sqlite3 thay vì pyodbc
import re
import os       # <-- THAY ĐỔI: Thêm 'os' để đọc PORT khi deploy
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
translator = Translator()

# <-- THAY ĐỔI: Kết nối SQLite
# Đảm bảo file database (ví dụ: 'database1.db') nằm cùng thư mục với app.py
# 'check_same_thread=False' là bắt buộc khi dùng SQLite với Flask
conn = sqlite3.connect('database1.db', check_same_thread=False)


def get_terms(module_id=None, page=1, per_page=10):
    cursor = conn.cursor()
    offset = (page - 1) * per_page

    # 1️⃣ Lấy dữ liệu chính
    if module_id:
        # <-- THAY ĐỔI: Sửa cú pháp SQL Server "OFFSET...FETCH" thành "LIMIT...OFFSET" của SQLite
        cursor.execute("""
            SELECT id, english, vietnamese, note, boi_canh, vi_du
            FROM Terms
            WHERE module = ?
            ORDER BY english ASC
            LIMIT ? OFFSET ?
        """, (module_id, per_page, offset)) # <-- THAY ĐỔI: Thứ tự 'per_page' và 'offset'
        terms = cursor.fetchall()

        # 2️⃣ Lấy tổng số bản ghi
        cursor.execute("SELECT COUNT(*) FROM Terms WHERE module = ?", (module_id,))
        total_count = cursor.fetchone()[0]
    else:
        # <-- THAY ĐỔI: Sửa cú pháp SQL Server "OFFSET...FETCH" thành "LIMIT...OFFSET" của SQLite
        cursor.execute("""
            SELECT id, english, vietnamese, note, boi_canh, vi_du, module
            FROM Terms
            ORDER BY english ASC
            LIMIT ? OFFSET ?
        """, (per_page, offset)) # <-- THAY ĐỔI: Thứ tự 'per_page' và 'offset'
        terms = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM Terms")
        total_count = cursor.fetchone()[0]

    total_pages = (total_count + per_page - 1) // per_page
    return terms, total_pages


def preprocess_terms(text, module_id=None):
    placeholders = {}
    lower_text = text.lower()
    cursor = conn.cursor()
    if module_id:
        cursor.execute("SELECT english, vietnamese, note FROM Terms WHERE module = ?", (module_id,))
    else:
        cursor.execute("SELECT english, vietnamese, note FROM Terms")

    terms = cursor.fetchall()

    for i, (english, vietnamese, note) in enumerate(terms):
        eng_lower = english.lower()
        if eng_lower in lower_text:
            placeholder = f"[[TERM{i}]]"
            # Cần xử lý cẩn thận hơn để tránh thay thế chồng chéo
            # Tạm thời vẫn dùng replace đơn giản
            lower_text = lower_text.replace(eng_lower, placeholder)
            
            # Tooltip: hiện english + note khi hover
            tooltip_text = f"{english} - {note}" if note else english
            placeholders[placeholder] = f"<span data-bs-toggle='tooltip' title='{tooltip_text}'><b>{vietnamese}</b></span>"
            
    return lower_text, placeholders


def postprocess_terms(text, placeholders):
    for placeholder, replacement in placeholders.items():
        pattern = re.compile(re.escape(placeholder), re.IGNORECASE)
        text = pattern.sub(replacement, text)
    return text

@app.route("/", methods=["GET", "POST"])
def index():
    result = ""
    if request.method == "POST":
        input_text = request.form["text"]
        module_id = request.form.get("module")  # lấy module được chọn

        # Nếu module_id có giá trị thì ép về int, còn không thì để None
        module_id = int(module_id) if module_id else None

        # Nếu người dùng không nhập gì thì tránh xử lý
        if not input_text:
            result = "<i>Vui lòng nhập văn bản cần dịch.</i>"
        else:
            
            pre_text, placeholders = preprocess_terms(input_text, module_id)
            translated = translator.translate(pre_text, src="en", dest="vi").text
            result = postprocess_terms(translated, placeholders)
    return render_template("index.html", result=result)

@app.route("/modules", methods=["GET", "POST"])
def modules():
    cursor = conn.cursor()

    # Lấy danh sách tất cả module để hiển thị
    cursor.execute("SELECT DISTINCT module FROM Terms ORDER BY module")
    modules = [row[0] for row in cursor.fetchall()]

    # Biến chứa kết quả tìm kiếm
    search_term = None
    results = []

    if request.method == "POST":
        search_term = request.form.get("term", "").strip()
        if search_term:
            cursor.execute("""
                SELECT module, english, vietnamese, boi_canh, vi_du
                FROM Terms
                WHERE LOWER(english) LIKE ?
                ORDER BY module, english
            """, (f"%{search_term.lower()}%",)) # Placeholder ? cần một tuple
            results = cursor.fetchall()

    return render_template("modules.html",
                           modules=modules,
                           search_term=search_term,
                           results=results)

@app.route("/terms/<int:module_id>", methods=["GET", "POST"])
def terms(module_id):
    page = int(request.args.get("page", 1))
    per_page = 10
    cursor = conn.cursor()

    query = ""
    if request.method == "POST":
        query = request.form.get("term", "").strip().lower()
        cursor.execute("""
            SELECT id, english, vietnamese, note, boi_canh, vi_du
            FROM Terms
            WHERE module = ? AND (LOWER(english) LIKE ? OR LOWER(vietnamese) LIKE ?)
            ORDER BY english ASC
        """, (module_id, f"%{query}%", f"%{query}%"))
        terms = cursor.fetchall()
        total_pages = 1
    else:
        terms, total_pages = get_terms(module_id, page, per_page)

    return render_template(
        "terms.html",
        module_id=module_id,
        terms=terms,
        query=query,
        page=page,
        total_pages=total_pages
    )

@app.route("/api/translate", methods=["POST"])
def api_translate():
    data = request.json
    
    # <-- THAY ĐỔI: Sửa lại logic nhận và dịch (đã bị lỗi ở phiên bản trước)
    # Giả sử API nhận một chuỗi văn bản lớn
    text_to_translate = data.get("text", "") 
    if not text_to_translate.strip():
        return jsonify({"translated_text": ""})

    # Tạm thời không lọc theo module_id trong API, bạn có thể thêm logic này sau
    pre_text, placeholders = preprocess_terms(text_to_translate, module_id=None)
    translated = translator.translate(pre_text, src="en", dest="vi").text
    final_text = postprocess_terms(translated, placeholders)

    return jsonify({"translated_text": final_text})


if __name__ == "__main__":
    # <-- THAY ĐỔI: Đọc PORT từ biến môi trường để deploy lên Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
