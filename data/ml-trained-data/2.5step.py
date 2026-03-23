import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.linear_model import LogisticRegression
import joblib

df = pd.read_csv("izmir_prepared_4class.csv")

# -------------------------
# MODEL 1: FIRE vs NO_FIRE
# -------------------------
df["target_fire"] = (df["risk_class"] != "NO_FIRE").astype(int)

X1 = df[["center_lat", "center_lon", "clc_code", "lc_group", "burnable"]].copy()
y1 = df["target_fire"]

num1 = ["center_lat", "center_lon"]
cat1 = ["clc_code", "lc_group", "burnable"]

pre1 = ColumnTransformer([
    ("num", Pipeline([("imp", SimpleImputer(strategy="median"))]), num1),
    ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                      ("oh", OneHotEncoder(handle_unknown="ignore"))]), cat1)
])

m1 = LogisticRegression(max_iter=2000, class_weight="balanced")
clf1 = Pipeline([("pre", pre1), ("model", m1)])

X1_tr, X1_te, y1_tr, y1_te = train_test_split(
    X1, y1, test_size=0.2, random_state=42, stratify=y1
)

clf1.fit(X1_tr, y1_tr)
p1 = clf1.predict(X1_te)

print("\n=== MODEL 1: FIRE vs NO_FIRE ===")
print("Accuracy:", accuracy_score(y1_te, p1))
print(classification_report(y1_te, p1))
print("Confusion Matrix:\n", confusion_matrix(y1_te, p1))

joblib.dump(clf1, "model_fire_vs_nofire.joblib")
print("Kaydedildi: model_fire_vs_nofire.joblib")

# -------------------------
# MODEL 2: HIGH vs LOW (only fire rows)
# -------------------------
df_fire = df[df["target_fire"] == 1].copy()
df_fire = df_fire[df_fire["risk_class"].isin(["HIGH", "LOW"])].copy()

X2 = df_fire[["center_lat", "center_lon", "fire_count", "max_frp", "mean_frp",
              "clc_code", "lc_group", "burnable"]].copy()
y2 = df_fire["risk_class"]

num2 = ["center_lat", "center_lon", "fire_count", "max_frp", "mean_frp"]
cat2 = ["clc_code", "lc_group", "burnable"]

pre2 = ColumnTransformer([
    ("num", Pipeline([("imp", SimpleImputer(strategy="median"))]), num2),
    ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                      ("oh", OneHotEncoder(handle_unknown="ignore"))]), cat2)
])

m2 = LogisticRegression(max_iter=2000, class_weight="balanced")
clf2 = Pipeline([("pre", pre2), ("model", m2)])

X2_tr, X2_te, y2_tr, y2_te = train_test_split(
    X2, y2, test_size=0.2, random_state=42, stratify=y2
)

clf2.fit(X2_tr, y2_tr)
p2 = clf2.predict(X2_te)

print("\n=== MODEL 2: HIGH vs LOW (only FIRE) ===")
print("Accuracy:", accuracy_score(y2_te, p2))
print(classification_report(y2_te, p2))
print("Confusion Matrix:\n", confusion_matrix(y2_te, p2))

joblib.dump(clf2, "model_high_vs_low.joblib")
print("Kaydedildi: model_high_vs_low.joblib")
