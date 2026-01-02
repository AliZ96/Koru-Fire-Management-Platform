import pandas as pd
import numpy as np
import joblib

# 1) Veriyi oku
df = pd.read_csv("izmir_prepared_4class.csv")

# 2) Modelleri yükle
clf_fire = joblib.load("model_fire_vs_nofire.joblib")
clf_hl = joblib.load("model_high_vs_low.joblib")

# -------------------------
# 3) FIRE olasılığı
# -------------------------
X_fire = df[["center_lat", "center_lon", "clc_code", "lc_group", "burnable"]].copy()

# predict_proba -> sınıf 1 olasılığı (FIRE)
fire_prob = clf_fire.predict_proba(X_fire)[:, 1]
df["fire_prob"] = fire_prob

# -------------------------
# 4) HIGH|FIRE olasılığı
# -------------------------
# Model 2 sadece HIGH/LOW öğrendi, o yüzden tüm grid için hesaplarız
X_hl = df[["center_lat", "center_lon", "fire_count", "max_frp", "mean_frp",
           "clc_code", "lc_group", "burnable"]].copy()

probs_hl = clf_hl.predict_proba(X_hl)
classes_hl = list(clf_hl.named_steps["model"].classes_)

# HIGH olasılığının hangi kolonda olduğunu bul
high_index = classes_hl.index("HIGH")
df["high_given_fire_prob"] = probs_hl[:, high_index]

# -------------------------
# 5) Final risk skoru
# -------------------------
# High risk score = P(FIRE) * P(HIGH|FIRE)
df["high_risk_score"] = df["fire_prob"] * df["high_given_fire_prob"]

# -------------------------
# 6) Etikete çevir (basit kural)
# -------------------------
# burnable=0 -> SAFE_UNBURNABLE
# burnable=1 ve fire_prob küçük -> SAFE_BURNABLE
# burnable=1 ve fire_prob büyük -> LOW/HIGH risk (high_risk_score ile)
FIRE_THRESHOLD = 0.50      # istersek sonra ayarlarız
HIGH_SCORE_THRESHOLD = 0.35  # istersek sonra ayarlarız

def final_label(row):
    if int(row["burnable"]) == 0:
        return "SAFE_UNBURNABLE"

    # burnable=1
    if row["fire_prob"] < FIRE_THRESHOLD:
        return "SAFE_BURNABLE"

    # fire ihtimali yüksekse risk seviyesi belirle
    return "HIGH_RISK" if row["high_risk_score"] >= HIGH_SCORE_THRESHOLD else "LOW_RISK"

df["predicted_risk"] = df.apply(final_label, axis=1)

# 7) Sadece gerekli kolonlar (harita için)
out_cols = [
    "center_lat", "center_lon",
    "burnable", "lc_group", "clc_code",
    "fire_prob", "high_given_fire_prob", "high_risk_score",
    "predicted_risk"
]
out = df[out_cols].copy()

# 8) Kaydet
out.to_csv("izmir_risk_map.csv", index=False)
print("Kaydedildi: izmir_risk_map.csv")

# 9) Özet
print("\nPredicted risk dağılımı:")
print(out["predicted_risk"].value_counts())
print("\nHigh risk score (min/mean/max):",
      out["high_risk_score"].min(),
      out["high_risk_score"].mean(),
      out["high_risk_score"].max())
