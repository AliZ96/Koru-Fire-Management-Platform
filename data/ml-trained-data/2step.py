import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
import joblib

# 1) Veri oku
df = pd.read_csv("izmir_prepared_4class.csv")

# 2) Hedef ve özellikler
y = df["target_4class"]

# Modelin kullanacağı feature’lar:
# - Konum (center_lat, center_lon) -> Harita üzerinde öğrenmesi için önemli
# - Land cover -> yangın riskiyle ilişkili
# - fire_count/conf/frp -> geçmiş yangın gücüyle ilişkili
feature_cols = [
    "center_lat", "center_lon",
    "fire_count", "max_conf", "mean_conf", "max_frp", "mean_frp",
    "clc_code", "lc_group", "burnable"
]
X = df[feature_cols].copy()

# 3) Sayısal / kategorik ayır
numeric_features = ["center_lat", "center_lon", "fire_count", "max_conf", "mean_conf", "max_frp", "mean_frp"]
categorical_features = ["clc_code", "lc_group", "burnable"]

# 4) Preprocess: eksik varsa doldur + kategorikleri OneHot
numeric_transformer = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="median"))
])

categorical_transformer = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("onehot", OneHotEncoder(handle_unknown="ignore"))
])

preprocess = ColumnTransformer(
    transformers=[
        ("num", numeric_transformer, numeric_features),
        ("cat", categorical_transformer, categorical_features)
    ]
)

# 5) Model: RandomForest (başlangıç için sağlam)
# class_weight="balanced" -> dengesiz sınıflar için önemli
model = RandomForestClassifier(
    n_estimators=300,
    random_state=42,
    class_weight="balanced",
    n_jobs=-1
)

clf = Pipeline(steps=[
    ("preprocess", preprocess),
    ("model", model)
])

# 6) Train/Test split (stratify çok önemli!)
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# 7) Eğit
clf.fit(X_train, y_train)

# 8) Tahmin + metrik
y_pred = clf.predict(X_test)

acc = accuracy_score(y_test, y_pred)
print("\nAccuracy:", acc)

print("\nClassification Report:")
print(classification_report(y_test, y_pred))

print("\nConfusion Matrix (rows=true, cols=pred):")
print(confusion_matrix(y_test, y_pred))

# 9) Modeli kaydet
joblib.dump(clf, "model_baseline.joblib")
print("\nKaydedildi: model_baseline.joblib")
