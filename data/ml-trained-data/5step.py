import pandas as pd
import folium
from folium.plugins import MarkerCluster

# 1) Veri oku
df = pd.read_csv("izmir_risk_map.csv")

# 2) Haritayı İzmir merkezine yakın başlat
center_lat = df["center_lat"].mean()
center_lon = df["center_lon"].mean()

m = folium.Map(location=[center_lat, center_lon], zoom_start=9, tiles="OpenStreetMap")

# 3) Sadece riskli noktalar (harita kalabalığını azaltır)
risk_df = df[df["predicted_risk"].isin(["LOW_RISK", "HIGH_RISK"])].copy()

# 4) Cluster (yakınken gruplanır, zoom yapınca açılır)
cluster = MarkerCluster(name="Risk Points").add_to(m)

def color_for(label):
    if label == "HIGH_RISK":
        return "red"
    if label == "LOW_RISK":
        return "orange"
    return "blue"

# 5) Noktaları ekle
for _, row in risk_df.iterrows():
    lat = row["center_lat"]
    lon = row["center_lon"]

    fire_prob = float(row["fire_prob"])
    high_prob = float(row["high_given_fire_prob"])
    score = float(row["high_risk_score"])
    label = row["predicted_risk"]

    popup_html = f"""
    <b>Predicted Risk:</b> {label}<br>
    <b>fire_prob (P(FIRE)):</b> {fire_prob:.3f}<br>
    <b>high_given_fire_prob (P(HIGH|FIRE)):</b> {high_prob:.3f}<br>
    <b>high_risk_score:</b> {score:.3f}<br>
    <b>burnable:</b> {int(row["burnable"])}<br>
    <b>lc_group:</b> {row["lc_group"]}<br>
    <b>clc_code:</b> {row["clc_code"]}
    """

    folium.CircleMarker(
        location=[lat, lon],
        radius=5 if label == "HIGH_RISK" else 4,
        color=color_for(label),
        fill=True,
        fill_opacity=0.8,
        popup=folium.Popup(popup_html, max_width=350)
    ).add_to(cluster)

# 6) Layer kontrol
folium.LayerControl().add_to(m)

# 7) Kaydet
out_file = "izmir_risk_interactive.html"
m.save(out_file)
print("Kaydedildi:", out_file)
