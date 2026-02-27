import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("izmir_risk_map.csv")

# 1) Sınıf bazlı scatter (renkleri otomatik atanır)
plt.figure(figsize=(10, 8))
for label, sub in df.groupby("predicted_risk"):
    plt.scatter(sub["center_lon"], sub["center_lat"], s=6, alpha=0.6, label=label)

plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.title("Izmir Grid - Predicted Risk Classes")
plt.legend(markerscale=3)
plt.tight_layout()
plt.savefig("risk_map_predicted.png", dpi=200)
plt.show()

# 2) Score bazlı scatter (high_risk_score)
plt.figure(figsize=(10, 8))
sc = plt.scatter(
    df["center_lon"], df["center_lat"],
    c=df["high_risk_score"], s=6, alpha=0.8
)
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.title("Izmir Grid - High Risk Score (P(FIRE)*P(HIGH|FIRE))")
plt.colorbar(sc, label="high_risk_score")
plt.tight_layout()
plt.savefig("risk_map_score.png", dpi=200)
plt.show()

print("Kaydedildi: risk_map_predicted.png ve risk_map_score.png")
