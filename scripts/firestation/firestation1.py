import os
import pandas as pd
import matplotlib.pyplot as plt

# --- Dosya yollarını "script'in bulunduğu klasöre" göre ayarla ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FIRE_CSV = os.path.join(BASE_DIR, "izmir_itfaiye_master_dataset.csv")
GRID_CSV = os.path.join(BASE_DIR, "izmir_ground_accessibility_v1.csv")

# --- CSV oku ---
fire = pd.read_csv(FIRE_CSV)
grid = pd.read_csv(GRID_CSV)

# --- Kolonları sayısala çevir (hata varsa NaN yapar) ---
fire["latitude"] = pd.to_numeric(fire["latitude"], errors="coerce")
fire["longitude"] = pd.to_numeric(fire["longitude"], errors="coerce")

grid["center_lat"] = pd.to_numeric(grid["center_lat"], errors="coerce")
grid["center_lon"] = pd.to_numeric(grid["center_lon"], errors="coerce")

# --- Geçersiz satırları ele ---
fire = fire.dropna(subset=["latitude", "longitude"])
grid = grid.dropna(subset=["center_lat", "center_lon"])

# --- Çizim ---
plt.figure(figsize=(10, 8))

# 1) Grid katmanı (varsa sınıfa göre renklendir)
if "ground_access_class" in grid.columns:
    grid["ground_access_class"] = grid["ground_access_class"].astype(str).str.upper()

    low = grid[grid["ground_access_class"] == "LOW"]
    med = grid[grid["ground_access_class"] == "MEDIUM"]
    high = grid[grid["ground_access_class"] == "HIGH"]
    other = grid[~grid["ground_access_class"].isin(["LOW", "MEDIUM", "HIGH"])]

    plt.scatter(low["center_lon"],  low["center_lat"],  s=8, marker="o", label="Grid LOW", alpha=0.7)
    plt.scatter(med["center_lon"],  med["center_lat"],  s=8, marker="o", label="Grid MEDIUM", alpha=0.7)
    plt.scatter(high["center_lon"], high["center_lat"], s=8, marker="o", label="Grid HIGH", alpha=0.7)

    if len(other) > 0:
        plt.scatter(other["center_lon"], other["center_lat"], s=8, marker="o", label="Grid OTHER", alpha=0.4)
else:
    # ground_access_class yoksa tek renk çiz
    plt.scatter(grid["center_lon"], grid["center_lat"], s=8, marker="o", label="Grid Points", alpha=0.7)

# 2) İtfaiye istasyonları (üst katman)
plt.scatter(
    fire["longitude"],
    fire["latitude"],
    s=120,
    marker="*",
    label="Fire Stations",
    edgecolors="black",
    linewidths=0.6,
)

plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.title("Izmir Ground Accessibility Grid + Fire Stations")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()