import pandas as pd
import requests
import os
from deep_translator import GoogleTranslator
from bs4 import BeautifulSoup
import time

# ---------------------------------------------------------------------------
# BƯỚC 1: CẤU HÌNH API CỦA BẠN
# ---------------------------------------------------------------------------
MY_API_URL = "https://apidichtienganh.onrender.com/api/translate"
MY_API_HEADERS = {"Content-Type": "application/json"}  # header chuẩn JSON

# ---------------------------------------------------------------------------
# BƯỚC 2: CÁC HÀM HỖ TRỢ
# ---------------------------------------------------------------------------
def translate_with_google(term):
    try:
        return GoogleTranslator(source='en', target='vi').translate(term)
    except Exception as e:
        return f"Lỗi Google ({e})"

def translate_with_my_api(term):
    payload = {"texts": [term]}  # API yêu cầu mảng "texts"
    try:
        response = requests.post(MY_API_URL, headers=MY_API_HEADERS, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            translations = data.get("translations", [])
            if translations and "content" in translations[0]:
                return translations[0]["content"]
            return "lỗi API"
        return f"Lỗi HTTP {response.status_code}"
    except Exception as e:
        return f"Lỗi kết nối ({e})"

def extract_text_from_html(html_content):
    """Lấy text thuần từ HTML"""
    return BeautifulSoup(html_content, "html.parser").get_text()

def load_test_corpus(filename):
    if not os.path.exists(filename):
        print(f"⚠ Không tìm thấy file {filename}. Bỏ qua nhóm này.")
        return []
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

# ---------------------------------------------------------------------------
# BƯỚC 3: SO SÁNH THEO NHÓM
# ---------------------------------------------------------------------------
def run_comparison_by_group():
    groups_to_test = {
        "Nhóm 1: Cơ bản": "basic.txt",
        "Nhóm 2: Chuyên sâu": "advanced.txt",
        "Nhóm 3: Viết tắt": "acronyms.txt",
        "Nhóm 4: Đa nghĩa": "polysemy.txt"
    }

    all_results = []
    group_stats = {}  # để thống kê %

    for group_name, filename in groups_to_test.items():
        terms = load_test_corpus(filename)
        if not terms:
            continue

        print(f"\n🔹 Đang xử lý {group_name} ({len(terms)} từ)")
        match_count = 0

        for term in terms:
            my_api_html = translate_with_my_api(term)
            my_api_text = extract_text_from_html(my_api_html).strip()
            google_trans = translate_with_google(term).strip()

            is_match = my_api_text.lower() == google_trans.lower()
            if is_match:
                match_count += 1

            all_results.append({
                "Nhóm": group_name,
                "Thuật ngữ (Term)": term,
                "My API": my_api_text,
                "Google": google_trans,
                "So khớp": "✅ Giống" if is_match else "❌ Khác"
            })

            print(f"   > {term:<20} | My API: {my_api_text:<25} | Google: {google_trans:<25} | {'✅' if is_match else '❌'}")

        # Tính % cho nhóm này
        accuracy = round((match_count / len(terms)) * 100, 2)
        group_stats[group_name] = accuracy
        print(f"📊 Độ chính xác nhóm này: {accuracy}% ({match_count}/{len(terms)})")

        time.sleep(1)  # nghỉ nhẹ để tránh spam

    return pd.DataFrame(all_results), group_stats

# ---------------------------------------------------------------------------
# BƯỚC 4: XUẤT BÁO CÁO
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    df, stats = run_comparison_by_group()

    if df.empty:
        print("\n⚠ Không có dữ liệu để báo cáo.")
    else:
        print("\n--- KẾT QUẢ DỊCH THEO NHÓM ---")
        print(df.to_string(index=False))

        try:
            # Xuất file chính
            df.to_excel("api_google_group_comparison.xlsx", index=False)

            # Xuất thống kê %
            stats_df = pd.DataFrame(list(stats.items()), columns=["Nhóm", "Độ chính xác (%)"])
            stats_df.loc[len(stats_df)] = ["Toàn bộ", round(sum(stats.values()) / len(stats), 2)]
            stats_df.to_excel("api_google_accuracy_summary.xlsx", index=False)

            print("\n✅ Đã lưu kết quả ra:")
            print("   → api_google_group_comparison.xlsx (so sánh chi tiết)")
            print("   → api_google_accuracy_summary.xlsx (thống kê %)")

        except Exception as e:
            print(f"\n❌ Không thể xuất Excel: {e}\n→ Cài thêm: pip install openpyxl")
