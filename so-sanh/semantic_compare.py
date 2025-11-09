import pandas as pd
from sentence_transformers import SentenceTransformer, util
from tqdm import tqdm

# === CẤU HÌNH ===
INPUT_FILE = "api_google_group_comparison.xlsx"   # phải có cột 'Google' và 'My API'
OUTPUT_FILE = "ketqua_semantic.xlsx"

# === TẢI MÔ HÌNH NGÔN NGỮ ===
print("🔹 Đang tải mô hình ngôn ngữ ...")
model = SentenceTransformer("keepitreal/vietnamese-sbert")

# === ĐỌC FILE ===
df = pd.read_excel(INPUT_FILE)

# Đảm bảo có hai cột
if not {'Google', 'My API'}.issubset(df.columns):
    raise Exception("⚠️ File phải có cột: 'Kết quả Google' và 'Kết quả My API'")

scores = []

# === TÍNH SIMILARITY TỪNG DÒNG ===
print("🔍 Đang so sánh ngữ nghĩa...")
for g, m in tqdm(zip(df['Google'], df['My API']), total=len(df)):
    if pd.isna(g) or pd.isna(m):
        scores.append(None)
        continue

    emb1 = model.encode(str(g), convert_to_tensor=True)
    emb2 = model.encode(str(m), convert_to_tensor=True)
    similarity = util.cos_sim(emb1, emb2).item()
    scores.append(round(similarity * 100, 2))  # đổi sang %

df['Độ tương đồng (%)'] = scores

# === ĐÁNH GIÁ SƠ BỘ ===
def rank(score):
    if score is None:
        return "-"
    elif score >= 85:
        return "✅ Giống nhau (rất sát nghĩa)"
    elif score >= 65:
        return "⚖️ Tạm tương đương"
    else:
        return "❌ Khác biệt"

df['Đánh giá sơ bộ'] = df['Độ tương đồng (%)'].apply(rank)

# === THỐNG KÊ TỔNG QUAN ===
total = len(df)
valid = df['Độ tương đồng (%)'].notna().sum()
avg_similarity = round(df['Độ tương đồng (%)'].mean(), 2)

high = (df['Độ tương đồng (%)'] >= 85).sum()
medium = ((df['Độ tương đồng (%)'] < 85) & (df['Độ tương đồng (%)'] >= 65)).sum()
low = (df['Độ tương đồng (%)'] < 65).sum()

summary = {
    "Tổng số thuật ngữ": total,
    "Số thuật ngữ hợp lệ": valid,
    "Similarity trung bình (%)": avg_similarity,
    "Số dòng giống nhau (>=85%)": int(high),
    "Số dòng tạm giống (65–85%)": int(medium),
    "Số dòng khác biệt (<65%)": int(low)
}

print("\n✅ === TỔNG QUAN ===")
for k, v in summary.items():
    print(f"{k}: {v}")

# Xuất summary ra Excel
summary_df = pd.DataFrame(list(summary.items()), columns=["Chỉ số", "Giá trị"])
summary_df.to_excel("overview_summary.xlsx", index=False)

# === XUẤT FILE KẾT QUẢ CHI TIẾT ===
df.to_excel(OUTPUT_FILE, index=False)
print(f"\n✅ Đã lưu chi tiết vào: {OUTPUT_FILE}")
print(f"✅ Đã lưu thống kê vào: overview_summary.xlsx")
