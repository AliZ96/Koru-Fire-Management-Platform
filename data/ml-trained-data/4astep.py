import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("izmir_risk_map.csv")

# SADECE riskli alanlar
risk_df = df[df["predicted_risk"].isin(["LOW_RISK", "HIGH_RISK"])]

plt.figure(figsize=(10, 8))

# LOW RISK
low = risk_df[risk_df["predicted_risk"] == "LOW_RISK"]
plt.scatter(
    low["center_lon"], low["center_lat"],
    c="orange", s=18, alpha=0.6, label="LOW RISK"
)

# HIGH RISK
high = risk_df[risk_df["predicted_risk"] == "HIGH_RISK"]
plt.scatter(
    high["center_lon"], high["center_lat"],
    c="red", s=22, alpha=0.9, label="HIGH RISK"
)

plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.title("Izmir – Potential Burn Risk Zones")
plt.legend()
plt.tight_layout()
plt.savefig("risk_map_clean.png", dpi=250)
plt.show()

print("Kaydedildi: risk_map_clean.png")
