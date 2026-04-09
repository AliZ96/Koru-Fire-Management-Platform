"""
routing_service.py
==================
İtfaiye istasyonlarından yangın risk noktalarına rota üretimi.

Yaklaşım:
  1. K-means → HIGH_RISK noktaları kümelenir (temsilci hedefler)
  2. Mesafe Matrisi → station × cluster (km)
  3. NetworkX Graf → station, LOW_RISK (geçiş), HIGH_RISK (hedef) düğümleri
  4. Dijkstra → en kısa yol (LOW → HIGH geçişleri dahil)
  5. Çıktı → rota, toplam mesafe, tahmini süre
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Optional

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

# ─── Sabitler ─────────────────────────────────────────────────────────────────
STATIONS_GEOJSON = (
    Path(__file__).resolve().parent.parent.parent
    / "static" / "data" / "fire-stations.geojson"
)
RISK_CSV = (
    Path(__file__).resolve().parent.parent.parent
    / "database" / "ml-map" / "izmir_future_fire_risk_dataset.csv"
)

AVG_SPEED_KMH: float = 60.0          # İtfaiye aracı ortalama hızı (km/h)
STATION_RADIUS_KM: float = 50.0      # İstasyon → LOW_RISK bağlantı yarıçapı
LOW_LOW_RADIUS_KM: float = 8.0       # LOW_RISK → LOW_RISK komşu bağlantı yarıçapı
LOW_HIGH_RADIUS_KM: float = 25.0     # LOW_RISK → HIGH_RISK bağlantı yarıçapı

# Risk düzeyi sıralaması (geçiş yönü kontrolü için)
RISK_LEVEL: Dict[str, int] = {
    "SAFE_UNBURNABLE": 0,
    "SAFE_BURNABLE": 1,
    "LOW_RISK": 2,
    "HIGH_RISK": 3,
}


# ─── Yardımcı Fonksiyonlar ────────────────────────────────────────────────────

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """İki coğrafi nokta arasındaki mesafeyi kilometre cinsinden döndürür."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# ─── Ana Sınıf ────────────────────────────────────────────────────────────────

class RoutingService:
    """
    İtfaiye → Risk Noktası Rota Servisi.

    Kullanım:
        svc = RoutingService(n_clusters=12)
        route = svc.route_station_to_target("station_1", "cluster_3")
    """

    def __init__(self, n_clusters: int = 12):
        self.n_clusters = n_clusters
        self.stations: List[Dict] = self._load_stations()
        self.risk_df: pd.DataFrame = self._load_risk_data()
        self.clusters: List[Dict] = []
        self.low_nodes: List[Dict] = []
        self.graph: nx.Graph = nx.Graph()
        self._build()

    # ── Veri Yükleme ─────────────────────────────────────────────────────────

    def _load_stations(self) -> List[Dict]:
        with open(STATIONS_GEOJSON, encoding="utf-8") as f:
            gj = json.load(f)
        stations = []
        for feat in gj["features"]:
            lon, lat = feat["geometry"]["coordinates"]
            stations.append(
                {
                    "id": f"station_{feat['properties']['id']}",
                    "name": feat["properties"]["name"],
                    "lat": lat,
                    "lon": lon,
                    "node_type": "station",
                }
            )
        return stations

    def _load_risk_data(self) -> pd.DataFrame:
        df = pd.read_csv(RISK_CSV)
        # Sadece yanabilir alanlar
        df = df[df["burnable"] == 1].copy()
        return df.reset_index(drop=True)

    # ── K-means: HIGH_RISK Kümeleme ──────────────────────────────────────────

    def _kmeans_high_risk(self) -> List[Dict]:
        """
        HIGH_RISK noktaları K-means ile kümelenir.
        Her küme için: merkez koordinatı, temsil noktası, küme büyüklüğü.
        Bu küme merkezleri "yangın hedefi" düğümlerine karşılık gelir.
        """
        high = self.risk_df[self.risk_df["predicted_risk_class"] == "HIGH_RISK"]
        if len(high) == 0:
            return []

        n = min(self.n_clusters, len(high))
        coords = high[["latitude", "longitude"]].values

        km = KMeans(n_clusters=n, random_state=42, n_init=10)
        km.fit(coords)
        centers = km.cluster_centers_   # (n, 2) → [lat, lon]
        labels = km.labels_

        clusters = []
        for i, center in enumerate(centers):
            mask = labels == i
            cluster_pts = high.iloc[np.where(mask)[0]]

            # Merkeze en yakın gerçek noktayı temsil noktası seç
            dists = cluster_pts.apply(
                lambda r: haversine(center[0], center[1], r["latitude"], r["longitude"]),
                axis=1,
            )
            rep = cluster_pts.iloc[dists.argmin()]

            clusters.append(
                {
                    "id": f"cluster_{i}",
                    "lat": float(rep["latitude"]),
                    "lon": float(rep["longitude"]),
                    "center_lat": float(center[0]),
                    "center_lon": float(center[1]),
                    "node_type": "HIGH_RISK",
                    "risk_class": "HIGH_RISK",
                    "combined_risk_score": float(cluster_pts["combined_risk_score"].mean()),
                    "fire_probability": float(cluster_pts["fire_probability"].mean()),
                    "cluster_size": int(mask.sum()),
                }
            )
        return clusters

    # ── Graf İnşası ───────────────────────────────────────────────────────────

    def _build(self) -> None:
        """
        Route grafını oluşturur (risk gradyanı topolojisi):
          • Düğümler: istasyonlar + LOW_RISK geçiş noktaları + HIGH_RISK küme merkezleri
          • Kenarlar:
              station  → LOW_RISK   (STATION_RADIUS_KM yarıçapında) — erişim kapısı
              LOW_RISK → LOW_RISK   (LOW_LOW_RADIUS_KM yarıçapında) — komşu geçiş
              LOW_RISK → HIGH_RISK  (LOW_HIGH_RADIUS_KM yarıçapında) — zon sınırı
              station  → HIGH_RISK  (yalnızca yedek; LOW yolu yoksa)
          • Kenar ağırlığı: haversine mesafe (km)
        """
        # 1. K-means ile HIGH_RISK küme merkezlerini üret
        self.clusters = self._kmeans_high_risk()

        # 2. LOW_RISK noktaları (geçiş waypoint'leri olarak)
        low = self.risk_df[self.risk_df["predicted_risk_class"] == "LOW_RISK"]
        self.low_nodes = [
            {
                "id": f"low_{i}",
                "lat": float(row["latitude"]),
                "lon": float(row["longitude"]),
                "node_type": "LOW_RISK",
                "risk_class": "LOW_RISK",
                "combined_risk_score": float(row["combined_risk_score"]),
                "fire_probability": float(row["fire_probability"]),
            }
            for i, (_, row) in enumerate(low.iterrows())
        ]

        G = nx.Graph()

        # Düğümleri ekle
        for s in self.stations:
            G.add_node(s["id"], **s)
        for ln in self.low_nodes:
            G.add_node(ln["id"], **ln)
        for c in self.clusters:
            G.add_node(c["id"], **c)

        # 1. İstasyon → LOW_RISK (erişim kapısı; doğrudan HIGH bağlantısı yok)
        for s in self.stations:
            for ln in self.low_nodes:
                d = haversine(s["lat"], s["lon"], ln["lat"], ln["lon"])
                if d <= STATION_RADIUS_KM:
                    G.add_edge(s["id"], ln["id"], weight=d, edge_type="station_to_low")

        # 2. LOW_RISK → LOW_RISK komşu bağlantıları (risk gradyanı geçişi)
        low_arr = [(ln["id"], ln["lat"], ln["lon"]) for ln in self.low_nodes]
        for i, (id_i, lat_i, lon_i) in enumerate(low_arr):
            for j in range(i + 1, len(low_arr)):
                id_j, lat_j, lon_j = low_arr[j]
                d = haversine(lat_i, lon_i, lat_j, lon_j)
                if d <= LOW_LOW_RADIUS_KM:
                    G.add_edge(id_i, id_j, weight=d, edge_type="low_to_low")

        # 3. LOW_RISK → HIGH_RISK geçişleri (zon sınırı)
        for ln in self.low_nodes:
            for c in self.clusters:
                d = haversine(ln["lat"], ln["lon"], c["lat"], c["lon"])
                if d <= LOW_HIGH_RADIUS_KM:
                    G.add_edge(ln["id"], c["id"], weight=d, edge_type="low_to_high")

        # 4. Yedek: istasyonun erişebildiği LOW düğümü yoksa doğrudan bağla
        for s in self.stations:
            if G.degree(s["id"]) == 0:
                for c in self.clusters:
                    d = haversine(s["lat"], s["lon"], c["lat"], c["lon"])
                    G.add_edge(s["id"], c["id"], weight=d, edge_type="station_to_high_fallback")

        self.graph = G

    # ── Mesafe Matrisi ────────────────────────────────────────────────────────

    def build_cost_matrix(self) -> Dict:
        """
        Station × Cluster mesafe matrisi (km).
        Her istasyon için en yakın küme de belirlenir.
        """
        matrix = []
        for s in self.stations:
            row: Dict = {
                "station_id": s["id"],
                "station_name": s["name"],
                "lat": s["lat"],
                "lon": s["lon"],
                "costs": {},
            }
            for c in self.clusters:
                d = haversine(s["lat"], s["lon"], c["lat"], c["lon"])
                row["costs"][c["id"]] = round(d, 3)

            nearest = min(row["costs"], key=row["costs"].get)
            row["nearest_cluster_id"] = nearest
            row["nearest_dist_km"] = row["costs"][nearest]
            row["estimated_travel_min"] = round(
                row["costs"][nearest] / AVG_SPEED_KMH * 60, 2
            )
            matrix.append(row)

        return {
            "station_count": len(self.stations),
            "cluster_count": len(self.clusters),
            "avg_speed_kmh": AVG_SPEED_KMH,
            "matrix": matrix,
        }

    # ── Rota Bulma ────────────────────────────────────────────────────────────

    def route_station_to_target(self, station_id: str, target_id: str) -> Dict:
        """
        Dijkstra ile istasyondan hedef HIGH_RISK kümesine en kısa yolu bulur.

        Dönüş:
          - path: rota üzerindeki düğümler (tip + koordinat bilgisiyle)
          - total_distance_km: toplam mesafe
          - travel_time_min: tahmini seyahat süresi
          - low_to_high_transitions: LOW→HIGH geçiş noktaları
        """
        if station_id not in self.graph:
            return {"error": f"İstasyon bulunamadı: {station_id}"}
        if target_id not in self.graph:
            return {"error": f"Hedef küme bulunamadı: {target_id}"}

        try:
            path_ids = nx.dijkstra_path(
                self.graph, station_id, target_id, weight="weight"
            )
            total_dist = nx.dijkstra_path_length(
                self.graph, station_id, target_id, weight="weight"
            )
        except nx.NetworkXNoPath:
            return {
                "error": "Rota bulunamadı",
                "station_id": station_id,
                "target_id": target_id,
            }

        # Düğüm verilerini ekle
        path_nodes = [dict(self.graph.nodes[nid]) for nid in path_ids]

        # LOW → HIGH geçişlerini tespit et
        transitions: List[Dict] = []
        for i in range(len(path_nodes) - 1):
            curr_type = path_nodes[i].get("risk_class", "station")
            next_type = path_nodes[i + 1].get("risk_class", "station")
            if curr_type == "LOW_RISK" and next_type == "HIGH_RISK":
                transitions.append(
                    {
                        "transition_index": i,
                        "from_node": path_nodes[i],
                        "to_node": path_nodes[i + 1],
                    }
                )

        travel_time_min = (total_dist / AVG_SPEED_KMH) * 60

        return {
            "station_id": station_id,
            "target_id": target_id,
            "path": path_nodes,
            "total_distance_km": round(total_dist, 3),
            "travel_time_min": round(travel_time_min, 2),
            "node_count": len(path_nodes),
            "low_to_high_transitions": transitions,
            "transition_count": len(transitions),
        }

    def find_nearest_station(self, lat: float, lon: float) -> Optional[Dict]:
        """Verilen koordinata en yakın itfaiye istasyonunu döndürür."""
        best: Optional[Dict] = None
        best_dist = float("inf")
        for s in self.stations:
            d = haversine(s["lat"], s["lon"], lat, lon)
            if d < best_dist:
                best_dist = d
                best = {**s, "distance_to_point_km": round(d, 3)}
        return best

    def find_nearest_cluster(self, lat: float, lon: float) -> Optional[Dict]:
        """Verilen koordinata en yakın HIGH_RISK kümesini döndürür."""
        best: Optional[Dict] = None
        best_dist = float("inf")
        for c in self.clusters:
            d = haversine(c["lat"], c["lon"], lat, lon)
            if d < best_dist:
                best_dist = d
                best = {**c, "distance_to_point_km": round(d, 3)}
        return best

    def route_all_stations_to_nearest_high(self) -> List[Dict]:
        """Her istasyonu, kendisine en yakın HIGH_RISK kümesine rotalandırır."""
        results = []
        for s in self.stations:
            nearest_cluster = self.find_nearest_cluster(s["lat"], s["lon"])
            if nearest_cluster:
                route = self.route_station_to_target(s["id"], nearest_cluster["id"])
                results.append(route)
        return results

    # ── Graf İstatistikleri ───────────────────────────────────────────────────

    def graph_summary(self) -> Dict:
        """Oluşturulan grafın özet bilgilerini döndürür."""
        return {
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "station_count": len(self.stations),
            "low_risk_node_count": len(self.low_nodes),
            "high_risk_cluster_count": len(self.clusters),
            "n_clusters_requested": self.n_clusters,
            "avg_speed_kmh": AVG_SPEED_KMH,
            "station_radius_km": STATION_RADIUS_KM,
            "low_low_radius_km": LOW_LOW_RADIUS_KM,
            "low_high_radius_km": LOW_HIGH_RADIUS_KM,
        }
