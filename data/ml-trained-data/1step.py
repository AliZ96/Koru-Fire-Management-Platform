import pandas as pd

# 1) CSV oku
path = "izmir_grid_with_landcover_burnable.csv"
df = pd.read_csv(path)

# 2) Hızlı kontrol
print("Shape:", df.shape)
print("Columns:", list(df.columns))
print("\nRisk class dağılımı:\n", df["risk_class"].value_counts(dropna=False))
print("\nBurnable dağılımı:\n", df["burnable"].value_counts(dropna=False))

# 3) 4 sınıflı hedef oluştur
def make_4class_label(row):
    rc = str(row["risk_class"]).upper()

    if rc == "NO_FIRE":
        # Safe bölgeyi burnable/unburnable diye ikiye ayır
        return "SAFE_BURNABLE" if int(row["burnable"]) == 1 else "SAFE_UNBURNABLE"

    # Yangın olanlar: HIGH / LOW
    if rc == "HIGH":
        return "HIGH"
    if rc == "LOW":
        return "LOW"

    # Beklenmeyen değer olursa (debug için)
    return "UNKNOWN"

df["target_4class"] = df.apply(make_4class_label, axis=1)

# 4) Son kontrol
print("\n4-class target dağılımı:\n", df["target_4class"].value_counts(dropna=False))

# 5) UNKNOWN var mı kontrol (olmaması lazım)
unknown_count = (df["target_4class"] == "UNKNOWN").sum()
print("\nUNKNOWN count:", unknown_count)

# 6) Temiz çıktı kaydet (bir sonraki aşamada bunu kullanacağız)
out_path = "izmir_prepared_4class.csv"
df.to_csv(out_path, index=False)
print("\nKaydedildi:", out_path)