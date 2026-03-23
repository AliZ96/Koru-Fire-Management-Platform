"""
Fire_state_kmeans.py
====================
Amaç:
  1. HIGH_RISK ve LOW_RISK noktaları K-means ile kümelenir (temsilci noktalar).
  2. İtfaiye istasyonları bu dosyaya gömülü CSV'den okunur.
  3. Tüm düğümlere (HIGH kümesi + LOW kümesi + istasyon) 1'den başlayan indis verilir.
  4. N×N kare mesafe matrisi oluşturulur; köşegen = 0.
  5. Simüle edilmiş YENİ bir yangın noktası:
       - fire_probability & combined_risk_score'a göre HIGH ya da LOW sınıflanır.
       - Matrise eklenerek tüm faal noktalara uzaklığı hesaplanır.
  6. Sonuçlar  output/distance_matrix.txt  dosyasına yazdırılır.
"""

import io
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

# ── Yollar ───────────────────────────────────────────────────────────────────
BASE       = Path(__file__).resolve().parent.parent.parent   # koru kök dizini
RISK_CSV   = BASE / "database" / "ml-map" / "izmir_future_fire_risk_dataset.csv"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_TXT = OUTPUT_DIR / "distance_matrix.txt"

# ── K-means Parametre ─────────────────────────────────────────────────────────
N_HIGH = 8    # HIGH_RISK temsilci küme sayısı
N_LOW  = 10   # LOW_RISK  temsilci küme sayısı

# ── Gömülü İtfaiye Verisi ─────────────────────────────────────────────────────
STATION_DATA = """\
station_name,latitude,longitude,verified_province,verified_district,is_in_izmir
6. Sanayi Sitesi İtfaiye Grubu,38.3458537,27.1398491,İzmir,Buca,True
Alosbi İtfaiye İstasyonu,38.8065108,27.0504836,İzmir,Aliağa,True
Balçova İtfaiye Grubu,38.3904733,27.0485545,İzmir,Balçova,True
Bayındır İtfaiye Grubu,38.2187664,27.6415279,İzmir,Bayındır,True
Bayraklı İtfaiye Grubu,38.451678,27.1767137,İzmir,Bayraklı,True
Bergama OSB İtfaiye Grubu,39.1077938,27.1937707,İzmir,Bergama,True
Beydağ İtfaiye Grubu,38.0858461,28.2110254,İzmir,Beydağ,True
Birgi İtfaiye Grubu,38.2530136,28.0658716,İzmir,Ödemiş,True
Bornova İtfaiye Müdürlüğü,38.4609301,27.2277298,İzmir,Bornova,True
Çamdibi İtfaiye Grubu,38.4257671,27.1829293,İzmir,Bornova,True
Çandarlı İtfaiye Müdürlüğü,38.9406527,26.9387285,İzmir,Dikili,True
Çaybaşı İtfaiye Grubu,38.1301752,27.385045,İzmir,Torbalı,True
Çeşme İtfaiye Grubu,38.3371806,26.3030841,İzmir,Çeşme,True
Çiğli İtfaiye Grubu,38.4919078,27.0411853,İzmir,Çiğli,True
Bostanlı İtfaiye Grubu,38.4872748,27.0748223,İzmir,Karşıyaka,True
Dikili İtfaiye Müdürlüğü,39.0781367,26.8966623,İzmir,Dikili,True
Evka-1 İtfaiye Grubu,38.3970338,27.1688458,İzmir,Buca,True
Evka-4 İtfaiye Grubu,38.4880259,27.214068,İzmir,Bornova,True
Foça İtfaiye Müdürlüğü,38.6662662,26.754763,İzmir,Foça,True
Gaziemir İtfaiye Grubu,38.3139969,27.1277295,İzmir,Gaziemir,True
Gümüldür İtfaiye Grubu,38.0704536,27.0007705,İzmir,Menderes,True
Güzelbahçe İtfaiye Grubu,38.3674545,26.8845373,İzmir,Güzelbahçe,True
Hatay İtfaiye Grubu,38.4020511,27.1149087,İzmir,Karabağlar,True
Ilıca İtfaiye Grubu,38.305354,26.361923,İzmir,Çeşme,True
Pınarbaşı İtfaiye Grubu,38.4304819,27.2396074,İzmir,Bornova,True
Deniz Arama Kurtarma Birimi,38.4136778,27.0237582,İzmir,Balçova,True
İTOB OSB İtfaiye Grubu,38.192774,27.2063271,İzmir,Menderes,True
Kadifekale İtfaiye Grubu,38.413057,27.139184,İzmir,Konak,True
Karabağlar İtfaiye Grubu,38.3926428,27.1343972,İzmir,Karabağlar,True
Karaburun İtfaiye Grubu,38.6365002,26.5106161,İzmir,Karaburun,True
Karşıyaka İtfaiyesi,38.4665598,27.134702,İzmir,Karşıyaka,True
Kemalpaşa OSB İtfaiye,38.455657,27.365967,İzmir,Kemalpaşa,True
Kınık İtfaiye,39.0883214,27.3742711,İzmir,Kınık,True
Kırklar İtfaiye Grubu,38.3092428,27.305661,İzmir,Buca,True
Kısıkköy İtfaiye Müdürlüğü,38.2751599,27.1971095,İzmir,Menderes,True
Menderes İtfaiye Grubu,38.2552038,27.1283411,İzmir,Menderes,True
Menemen İtfaiye Grubu,38.6114959,27.0747393,İzmir,Menemen,True
Mordoğan İtfaiye Grubu,38.5151347,26.6163012,İzmir,Karaburun,True
Narlıdere İtfaiye,38.3937204,27.016462,İzmir,Narlıdere,True
Ödemiş İtfaiyesi,38.2203779,27.9772609,İzmir,Ödemiş,True
Seferihisar İtfaiye Müdürlüğü,38.1932306,26.8449294,İzmir,Seferihisar,True
Selçuk İtfaiye Amirliği,37.9586131,27.3672035,İzmir,Selçuk,True
Seyrek İtfaiye Grubu,38.5885704,26.9735422,İzmir,Menemen,True
Tire İtfaiye Grubu,38.0947013,27.7445669,İzmir,Tire,True
Torbalı İtfaiye Grubu,38.1516848,27.3645769,İzmir,Torbalı,True
Toros İtfaiyesi (Buca),38.4055253,27.1917275,İzmir,Buca,True
Urla İtfaiye Grubu,38.3274799,26.7704619,İzmir,Urla,True
Yenifoça İtfaiye,38.7440082,26.8432607,İzmir,Foça,True
Hilal Merkez İtfaiye (Konak),38.422673,27.1538156,İzmir,Konak,True
"""

# ── Yardımcı: Haversine Mesafe (km) ──────────────────────────────────────────
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return round(2 * R * math.asin(math.sqrt(a)), 4)


# ── Yardımcı: Yeni Yangın Sınıflandır ────────────────────────────────────────
def classify_fire(fire_probability: float, combined_risk_score: float) -> str:
    """
    fire_probability ve combined_risk_score'a göre yeni yangın noktasını
    HIGH_RISK veya LOW_RISK olarak sınıflandır.
    Eşik değerleri ML dataset istatistiklerinden türetildi.
    """
    if fire_probability >= 0.75 or combined_risk_score >= 0.60:
        return "HIGH_RISK"
    return "LOW_RISK"


# ── Ana Fonksiyon ─────────────────────────────────────────────────────────────
def build_distance_matrix(
    new_fire_lat: float = 38.34,
    new_fire_lon: float = 27.18,
    new_fire_fire_prob: float = 0.82,
    new_fire_risk_score: float = 0.71,
):
    """
    Tüm düğümleri indeksleyip NxN mesafe matrisini oluşturur.
    Yeni yangın noktası matrise eklenerek tüm uzaklıklar hesaplanır.
    Sonuç distance_matrix.txt'e yazdırılır.
    """

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. Veri Yükle ─────────────────────────────────────────────────────────
    print("📂 Risk verisi yükleniyor...")
    df = pd.read_csv(RISK_CSV)
    df_burnable = df[df["burnable"] == 1].copy()

    high_df = df_burnable[df_burnable["predicted_risk_class"] == "HIGH_RISK"]
    low_df  = df_burnable[df_burnable["predicted_risk_class"] == "LOW_RISK"]

    # ── 2. K-means: HIGH ve LOW Kümele ────────────────────────────────────────
    print(f"🔵 K-means: {len(high_df)} HIGH_RISK → {N_HIGH} küme")
    km_high = KMeans(n_clusters=min(N_HIGH, len(high_df)), random_state=42, n_init=10)
    km_high.fit(high_df[["latitude", "longitude"]].values)
    high_centers = km_high.cluster_centers_   # (N_HIGH, 2)

    print(f"🟡 K-means: {len(low_df)} LOW_RISK → {N_LOW} küme")
    km_low = KMeans(n_clusters=min(N_LOW, len(low_df)), random_state=42, n_init=10)
    km_low.fit(low_df[["latitude", "longitude"]].values)
    low_centers = km_low.cluster_centers_     # (N_LOW, 2)

    # ── 3. İtfaiye İstasyonlarını Yükle ──────────────────────────────────────
    stations_df = pd.read_csv(io.StringIO(STATION_DATA))

    # ── 4. Yeni Yangın Sınıfla ────────────────────────────────────────────────
    new_fire_class = classify_fire(new_fire_fire_prob, new_fire_risk_score)
    print(f"🔥 Yeni yangın → {new_fire_class}  ({new_fire_lat}, {new_fire_lon})")

    # ── 5. Düğüm Listesi Oluştur ve İndeks Ver ────────────────────────────────
    # Sıralama: YENİ YANGIN | HIGH kümeler | LOW kümeler | İstasyonlar
    nodes = []

    # Yeni yangın noktası — indeks 1
    nodes.append({
        "index": 1,
        "label": f"YENİ_YANGIN ({new_fire_class})",
        "type": new_fire_class,
        "lat": new_fire_lat,
        "lon": new_fire_lon,
    })

    idx = 2
    for i, (lat, lon) in enumerate(high_centers):
        # Her küme için risk istatistiklerini bul
        cluster_pts = high_df.iloc[km_high.labels_ == i]
        nodes.append({
            "index": idx,
            "label": f"HIGH_KÜME_{i+1}",
            "type": "HIGH_RISK",
            "lat": round(float(lat), 6),
            "lon": round(float(lon), 6),
            "cluster_size": len(cluster_pts),
            "avg_risk_score": round(float(cluster_pts["combined_risk_score"].mean()), 4),
        })
        idx += 1

    for i, (lat, lon) in enumerate(low_centers):
        cluster_pts = low_df.iloc[km_low.labels_ == i]
        nodes.append({
            "index": idx,
            "label": f"LOW_KÜME_{i+1}",
            "type": "LOW_RISK",
            "lat": round(float(lat), 6),
            "lon": round(float(lon), 6),
            "cluster_size": len(cluster_pts),
            "avg_risk_score": round(float(cluster_pts["combined_risk_score"].mean()), 4),
        })
        idx += 1

    for _, row in stations_df.iterrows():
        nodes.append({
            "index": idx,
            "label": f"İTFAİYE: {row['station_name']}",
            "type": "STATION",
            "lat": float(row["latitude"]),
            "lon": float(row["longitude"]),
            "district": row["verified_district"],
        })
        idx += 1

    N = len(nodes)
    print(f"📊 Toplam düğüm: {N}  (1 yeni yangın + {N_HIGH} HIGH + {N_LOW} LOW + {len(stations_df)} istasyon)")

    # ── 6. NxN Mesafe Matrisi ─────────────────────────────────────────────────
    print("📐 Mesafe matrisi hesaplanıyor...")
    matrix = [[0.0] * N for _ in range(N)]
    for i in range(N):
        for j in range(N):
            if i == j:
                matrix[i][j] = 0.0
            elif j > i:
                d = haversine(nodes[i]["lat"], nodes[i]["lon"],
                              nodes[j]["lat"], nodes[j]["lon"])
                matrix[i][j] = d
                matrix[j][i] = d   # simetrik

    # ── 7. Metin Dosyasına Yaz ────────────────────────────────────────────────
    print(f"💾 Sonuçlar yazılıyor → {OUTPUT_TXT}")
    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:

        # Başlık
        f.write("=" * 80 + "\n")
        f.write("  KORU – Yangın Noktası & İtfaiye Mesafe Matrisi\n")
        f.write("  K-means (HIGH/LOW) + İtfaiye İstasyonları\n")
        f.write("=" * 80 + "\n\n")

        # ── Düğüm Dizini ──────────────────────────────────────────────────────
        f.write("── DÜĞÜM DİZİNİ ────────────────────────────────────────────────\n")
        f.write(f"{'İndeks':<8} {'Tip':<14} {'Etiket':<45} {'Lat':>10} {'Lon':>10}\n")
        f.write("-" * 90 + "\n")
        for n in nodes:
            f.write(
                f"{n['index']:<8} "
                f"{n['type']:<14} "
                f"{n['label']:<45} "
                f"{n['lat']:>10.6f} "
                f"{n['lon']:>10.6f}\n"
            )

        # ── Yeni Yangın Bilgisi ───────────────────────────────────────────────
        f.write("\n── YENİ YANGIN BİLGİSİ ─────────────────────────────────────────\n")
        f.write(f"  Konum          : ({new_fire_lat}, {new_fire_lon})\n")
        f.write(f"  fire_probability : {new_fire_fire_prob}\n")
        f.write(f"  combined_risk_score : {new_fire_risk_score}\n")
        f.write(f"  SINIF (K-means eşiği): {new_fire_class}\n")
        f.write(f"  Matris İndeksi : 1\n")

        # ── Yeni Yangın → Tüm Düğüm Uzaklıkları ──────────────────────────────
        f.write("\n── YENİ YANGIN (İndeks 1) → TÜM DÜĞÜMLER UZAKLIĞI (km) ─────────\n")
        f.write(f"{'İndeks':<8} {'Tip':<14} {'Etiket':<45} {'Uzaklık (km)':>14}\n")
        f.write("-" * 85 + "\n")
        fire_row = matrix[0]
        for n in nodes[1:]:  # kendisi hariç
            f.write(
                f"{n['index']:<8} "
                f"{n['type']:<14} "
                f"{n['label']:<45} "
                f"{fire_row[n['index']-1]:>14.4f}\n"
            )

        # ── En Yakın İtfaiyeler ───────────────────────────────────────────────
        station_nodes = [n for n in nodes if n["type"] == "STATION"]
        station_dists = [(n, fire_row[n["index"] - 1]) for n in station_nodes]
        station_dists.sort(key=lambda x: x[1])
        f.write("\n── EN YAKIN 5 İTFAİYE (Yeni Yangına) ──────────────────────────\n")
        f.write(f"{'Sıra':<6} {'İndeks':<8} {'İtfaiye Adı':<45} {'Uzaklık (km)':>14}\n")
        f.write("-" * 76 + "\n")
        for rank, (n, dist) in enumerate(station_dists[:5], 1):
            f.write(f"{rank:<6} {n['index']:<8} {n['label']:<45} {dist:>14.4f}\n")

        # ── En Yakın HIGH/LOW Kümeler ─────────────────────────────────────────
        risk_nodes = [n for n in nodes if n["type"] in ("HIGH_RISK", "LOW_RISK")]
        risk_dists = [(n, fire_row[n["index"] - 1]) for n in risk_nodes]
        risk_dists.sort(key=lambda x: x[1])
        f.write("\n── EN YAKIN 5 RİSK KÜMESİ (Yeni Yangına) ──────────────────────\n")
        f.write(f"{'Sıra':<6} {'İndeks':<8} {'Küme':<30} {'Uzaklık (km)':>14}\n")
        f.write("-" * 62 + "\n")
        for rank, (n, dist) in enumerate(risk_dists[:5], 1):
            f.write(f"{rank:<6} {n['index']:<8} {n['label']:<30} {dist:>14.4f}\n")

        # ── Tam NxN Matris ────────────────────────────────────────────────────
        f.write("\n" + "=" * 80 + "\n")
        f.write(f"  TAM {N}×{N} MESAFE MATRİSİ (km)  — köşegen = 0\n")
        f.write("  Satır = kaynak düğüm indeksi, Sütun = hedef düğüm indeksi\n")
        f.write("=" * 80 + "\n\n")

        # Sütun başlıkları
        header = f"{'':>6} " + " ".join(f"{n['index']:>8}" for n in nodes)
        f.write(header + "\n")
        f.write("-" * len(header) + "\n")

        for i, row_node in enumerate(nodes):
            row_str = f"{row_node['index']:>6} " + " ".join(
                f"{matrix[i][j]:>8.2f}" for j in range(N)
            )
            f.write(row_str + "\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("  AÇIKLAMA\n")
        f.write("  • İndeks 1              : Yeni yangın noktası\n")
        f.write(f"  • İndeks 2–{1+N_HIGH:<3}          : HIGH_RISK K-means küme merkezleri\n")
        f.write(f"  • İndeks {2+N_HIGH}–{1+N_HIGH+N_LOW:<3}         : LOW_RISK  K-means küme merkezleri\n")
        f.write(f"  • İndeks {2+N_HIGH+N_LOW}–{N:<3}         : İtfaiye istasyonları\n")
        f.write("  • Mesafe birimi         : km (Haversine formülü)\n")
        f.write("  • Köşegen               : 0.00 (düğüm kendine olan uzaklık)\n")
        f.write("  • Matris simetrik       : matrix[i][j] == matrix[j][i]\n")
        f.write("=" * 80 + "\n")

    print(f"✅ Tamamlandı! → {OUTPUT_TXT}")

    # Kısa özet konsola da bas
    print(f"\n{'='*55}")
    print(f"  ÖZET")
    print(f"{'='*55}")
    print(f"  Toplam düğüm           : {N}")
    print(f"  Yeni yangın sınıfı     : {new_fire_class} (İndeks 1)")
    print(f"  HIGH kümesi sayısı     : {N_HIGH}")
    print(f"  LOW kümesi sayısı      : {N_LOW}")
    print(f"  İtfaiye sayısı         : {len(stations_df)}")
    print(f"  En yakın istasyon      : {station_dists[0][0]['label']}")
    print(f"  Mesafe                 : {station_dists[0][1]:.4f} km")
    print(f"  Çıktı dosyası          : {OUTPUT_TXT}")
    print(f"{'='*55}")

    return nodes, matrix


# ── Çalıştır ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Simülasyon: Buca yakınlarında yeni bir yangın
    build_distance_matrix(
        new_fire_lat=38.34,
        new_fire_lon=27.18,
        new_fire_fire_prob=0.82,
        new_fire_risk_score=0.71,
    )
