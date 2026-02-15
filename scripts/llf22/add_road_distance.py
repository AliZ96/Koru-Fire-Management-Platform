import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import box
from shapely.strtree import STRtree

# ======================
# PATHS (senin repo yapına göre)
# ======================
GRID_CSV = "scripts/llf22/data/processed/izmir_grid_with_predictions_v2.csv"
ROADS_SHP = "scripts/llf22/data/raw/gis_osm_roads_free_1.shp"
OUT_CSV = "scripts/llf22/output/izmir_grid_with_road_distance_v1.csv"

# ======================
# SETTINGS
# ======================
UTM_EPSG = 32635          # Izmir için UTM 35N (metre)
BBOX_BUFFER_DEG = 0.30    # Roads'u hızlandırmak için grid bbox etrafına buffer (derece)


def main():
    # 1) GRID yükle
    df = pd.read_csv(GRID_CSV)
    if "center_lat" not in df.columns or "center_lon" not in df.columns:
        raise ValueError(
            f"Grid CSV 'center_lat' ve 'center_lon' içermeli. Bulunan kolonlar: {list(df.columns)}"
        )

    grid = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["center_lon"], df["center_lat"]),
        crs="EPSG:4326"
    )

    # 2) ROADS yükle
    roads = gpd.read_file(ROADS_SHP)
    roads = roads[roads.geometry.notna() & ~roads.geometry.is_empty].copy()
    roads = roads[roads.geometry.geom_type.isin(["LineString", "MultiLineString"])].copy()
    if roads.empty:
        raise ValueError("Roads dosyasında LineString/MultiLineString geometrisi bulunamadı.")

    # 3) Hız için: Roads'u Izmir grid bbox (+buffer) ile süz (WGS84 üstünde)
    minx, miny, maxx, maxy = grid.total_bounds  # lon/lat
    buf = float(BBOX_BUFFER_DEG)
    bbox = box(minx - buf, miny - buf, maxx + buf, maxy + buf)
    roads = roads[roads.intersects(bbox)].copy()
    if roads.empty:
        raise ValueError("BBox filtresinden sonra roads boş kaldı. Buffer'ı artırmayı deneyebilirsin.")

    print(f"[INFO] Roads after bbox prefilter: {len(roads)}")

    # 4) Metreyle distance için UTM'e projekte et
    grid_m = grid.to_crs(epsg=UTM_EPSG)
    roads_m = roads.to_crs(epsg=UTM_EPSG)

    # 5) En yakın yol mesafesi (Shapely 2 uyumlu)
    road_geoms = list(roads_m.geometry.values)
    tree = STRtree(road_geoms)

    distances = []
    for pt in grid_m.geometry.values:
        idx = tree.nearest(pt)          # Shapely 2: index dönebilir
        nearest_geom = road_geoms[idx]  # geometry'yi listeden çek
        distances.append(pt.distance(nearest_geom))

    # 6) Sonucu orijinal grid'e yaz (geometry yok CSV'de)
    grid["dist_to_road_m"] = distances

    # 7) Kaydet
    out_dir = os.path.dirname(OUT_CSV)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    grid.drop(columns=["geometry"]).to_csv(OUT_CSV, index=False)
    print(f"[DONE] Saved: {OUT_CSV}")
    print("[INFO] dist_to_road_m summary:")
    print(pd.Series(distances).describe())


if __name__ == "__main__":
    main()
