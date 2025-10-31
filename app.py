from flask import Flask, request, render_template, redirect, url_for, jsonify
from deep_translator import GoogleTranslator
import sqlite3  # <-- Dùng sqlite3
import re
import os       # <-- Thêm 'os' để đọc PORT
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
translator = GoogleTranslator(source='en', target='vi')

# --- Kết nối SQLite ---
# Đảm bảo file database (ví dụ: 'database1.db') nằm cùng thư mục
try:
    conn = sqlite3.connect('database1.db', check_same_thread=False)
except sqlite3.Error as e:
    print(f"Lỗi khi kết nối tới SQLite: {e}")
    # Bạn có thể muốn thoát ứng dụng nếu không kết nối được DB
    # exit(1)


def get_terms(module_id=None, page=1, per_page=10):
    cursor = conn.cursor()
    offset = (page - 1) * per_page
    terms = []
    total_count = 0

    try:
        # 1️⃣ Lấy dữ liệu chính
        if module_id:
            cursor.execute("""
                SELECT id, english, vietnamese, note, boi_canh, vi_du
                FROM Terms
                WHERE module = ?
                ORDER BY english ASC
                LIMIT ? OFFSET ?
            """, (module_id, per_page, offset))
            terms = cursor.fetchall()

            # 2️⃣ Lấy tổng số bản ghi
            cursor.execute("SELECT COUNT(*) FROM Terms WHERE module = ?", (module_id,))
            total_count = cursor.fetchone()[0]
        else:
            cursor.execute("""
                SELECT id, english, vietnamese, note, boi_canh, vi_du, module
                FROM Terms
                ORDER BY english ASC
                LIMIT ? OFFSET ?
            """, (per_page, offset))
            terms = cursor.fetchall()

            cursor.execute("SELECT COUNT(*) FROM Terms")
            total_count = cursor.fetchone()[0]
    except sqlite3.Error as e:
        print(f"Lỗi SQL trong get_terms: {e}")
        
    total_pages = (total_count + per_page - 1) // per_page
    return terms, total_pages


def preprocess_terms(text, module_id=None):
    placeholders = {}
    lower_text = text.lower()
    cursor = conn.cursor()
    terms = []

    try:
        if module_id:
            cursor.execute("SELECT english, vietnamese, note FROM Terms WHERE module = ?", (module_id,))
        else:
            cursor.execute("SELECT english, vietnamese, note FROM Terms")
        terms = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Lỗi SQL trong preprocess_terms: {e}")

    # Sắp xếp các term từ dài đến ngắn để ưu tiên khớp các cụm từ dài trước
    terms.sort(key=lambda x: len(x[0]), reverse=True)

    for i, (english, vietnamese, note) in enumerate(terms):
        eng_lower = english.lower()
        if eng_lower in lower_text:
            placeholder = f"[[TERM{i}]]"
            
            # Dùng regex để chỉ thay thế từ đứng riêng lẻ (word boundary)
            # Điều này phức tạp hơn và có thể cần tinh chỉnh
            # Tạm thời vẫn dùng replace đơn giản để tránh lỗi
            lower_text = lower_text.replace(eng_lower, placeholder)
            
            tooltip_text = f"{english} - {note}" if note else english
            # Escape HTML-sensitive characters in tooltip
            tooltip_text = (
                tooltip_text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\"", "&quot;")
            )
            
            placeholders[placeholder] = f"<span data-bs-toggle='tooltip' title='{tooltip_text}'><b>{vietnamese}</b></span>"
            
    return lower_text, placeholders


def postprocess_terms(text, placeholders):
    for placeholder, replacement in placeholders.items():
        # Dùng regex để thay thế không phân biệt hoa thường
        pattern = re.compile(re.escape(placeholder), re.IGNORECASE)
        text = pattern.sub(replacement, text)
    return text

@app.route("/", methods=["GET", "POST"])
def index():
    cursor = conn.cursor()
    modules = []
    try:
        # Lấy danh sách module cho dropdown
        cursor.execute("SELECT DISTINCT module FROM Terms ORDER BY module")
        modules = [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Lỗi SQL khi lấy modules cho index: {e}")

    result = ""
    input_text_content = "" # Giữ lại text đã nhập
    selected_module = None  # Giữ lại module đã chọn

    if request.method == "POST":
        input_text = request.form.get("text", "")
        input_text_content = input_text # Lưu lại
        module_id = request.form.get("module") 

        # Kiểm tra module_id hợp lệ trước khi ép kiểu
        module_id = int(module_id) if module_id and module_id.isdigit() else None
        selected_module = module_id # Lưu lại

        if not input_text.strip():
            result = "<i>Vui lòng nhập văn bản cần dịch.</i>"
        else:
            try:
                pre_text, placeholders = preprocess_terms(input_text, module_id)
                translated = translator.translate(pre_text, src="en", dest="vi").text
                result = postprocess_terms(translated, placeholders)
            except Exception as e:
                print(f"Lỗi khi dịch: {e}")
                result = f"<i class='text-danger'>Đã xảy ra lỗi trong quá trình dịch: {e}</i>"

    return render_template("index.html", 
                           result=result, 
                           modules=modules,
                           input_text=input_text_content,
                           selected_module=selected_module)

@app.route("/modules", methods=["GET", "POST"])
def modules():
    cursor = conn.cursor()
    modules_list = []
    try:
        cursor.execute("SELECT DISTINCT module FROM Terms ORDER BY module")
        modules_list = [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Lỗi SQL trong modules: {e}")

    search_term = None
    results = []

    if request.method == "POST":
        search_term = request.form.get("term", "").strip()
        if search_term:
            try:
                cursor.execute("""
                    SELECT module, english, vietnamese, note, vi_du
                    FROM Terms
                    WHERE LOWER(english) LIKE ?
                    ORDER BY module, english
                """, (f"%{search_term.lower()}%",))
                results = cursor.fetchall()
            except sqlite3.Error as e:
                print(f"Lỗi SQL khi tìm kiếm /modules: {e}")

    return render_template("modules.html",
                           modules=modules_list,
                           search_term=search_term,
                           results=results)

@app.route("/terms/<int:module_id>", methods=["GET", "POST"])
def terms(module_id):
    page = int(request.args.get("page", 1))
    per_page = 10
    cursor = conn.cursor()
    query_term = ""
    terms_list = []
    total_pages = 1

    try:
        if request.method == "POST":
            query_term = request.form.get("term", "").strip().lower()
            cursor.execute("""
                SELECT id, english, vietnamese, note, boi_canh, vi_du
                FROM Terms
                WHERE module = ? AND (LOWER(english) LIKE ? OR LOWER(vietnamese) LIKE ?)
                ORDER BY english ASC
            """, (module_id, f"%{query_term}%", f"%{query_term}%"))
            terms_list = cursor.fetchall()
            total_pages = 1
        else:
            terms_list, total_pages = get_terms(module_id, page, per_page)
    except sqlite3.Error as e:
        print(f"Lỗi SQL trong /terms/{module_id}: {e}")

    return render_template(
        "terms.html",
        module_id=module_id,
        terms=terms_list,
        query=query_term,
        page=page,
        total_pages=total_pages
    )

@app.route("/api/translate", methods=["POST"])
def api_translate():
    data = request.json
    text_to_translate = data.get("text", "") 
    if not text_to_translate.strip():
        return jsonify({"translated_text": ""})

    try:
        # API tạm thời không lọc theo module, có thể thêm sau
        pre_text, placeholders = preprocess_terms(text_to_translate, module_id=None)
        translated = translator.translate(pre_text, src="en", dest="vi").text
        final_text = postprocess_terms(translated, placeholders)
        return jsonify({"translated_text": final_text})
    except Exception as e:
        print(f"Lỗi API translate: {e}")
        return jsonify({"error": str(e)}), 500


# --- ✨ TÍNH NĂNG MỚI: API GỢI Ý TÌM KIẾM ---
@app.route("/api/suggestions", methods=["GET"])
def api_suggestions():
    """
    API trả về các gợi ý tìm kiếm (autocomplete).
    Nhận 'q' (query) và 'module_id' (tùy chọn).
    """
    query = request.args.get("q", "").strip().lower()
    module_id = request.args.get("module_id")

    if not query:
        return jsonify([]) # Trả về mảng rỗng nếu không có query

    cursor = conn.cursor()
    suggestions = []
    
    try:
        sql_query = """
            SELECT DISTINCT english 
            FROM Terms 
            WHERE LOWER(english) LIKE ?
        """
        # Thêm % vào cuối query để tìm các từ BẮT ĐẦU bằng query
        params = [f"{query}%"] 

        if module_id and module_id.isdigit():
            sql_query += " AND module = ?"
            params.append(int(module_id))

        sql_query += " ORDER BY english ASC LIMIT 10" # Giới hạn 10 kết quả
        
        cursor.execute(sql_query, tuple(params))
        suggestions = [row[0] for row in cursor.fetchall()]
        
    except sqlite3.Error as e:
        print(f"Lỗi SQL trong /api/suggestions: {e}")
        
    return jsonify(suggestions)
# --- ✨ KẾT THÚC TÍNH NĂNG MỚI ---


if __name__ == "__main__":
    # Đọc PORT từ biến môi trường
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True) # Thêm debug=True để dễ phát triển
