import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("izmir_risk_map.csv")

# Sadece burnable alanlar
df = df[df["burnable"] == 1]

plt.figure(figsize=(10, 8))

sc = plt.scatter(
    df["center_lon"], df["center_lat"],
    c=df["high_risk_score"],
    cmap="hot",
    s=20,
    alpha=0.8
)

plt.colorbar(sc, label="High Risk Score")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.title("Izmir – Fire Risk Intensity Map")
plt.tight_layout()
plt.savefig("risk_map_heat.png", dpi=250)
plt.show()

print("Kaydedildi: risk_map_heat.png")