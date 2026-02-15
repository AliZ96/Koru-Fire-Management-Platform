import os
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling

GRID_IN = "scripts/llf22/output/izmir_grid_with_road_distance_v1.csv"
DEM_IN = "scripts/llf22/data/raw/dem_izmir.tif"
DEM_UTM = "scripts/llf22/data/raw/dem_izmir_utm35.tif"

OUT_CSV = "scripts/llf22/output/izmir_grid_with_accessibility_inputs_v1.csv"

UTM35 = "EPSG:32635"  # İzmir için uygun (UTM zone 35N)


def reproject_dem_to_utm(dem_in: str, dem_out: str) -> None:
    """Reproject DEM to UTM so slope math uses meters."""
    with rasterio.open(dem_in) as src:
        dst_crs = UTM35
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds
        )

        kwargs = src.meta.copy()
        kwargs.update({
            "crs": dst_crs,
            "transform": transform,
            "width": width,
            "height": height
        })

        with rasterio.open(dem_out, "w", **kwargs) as dst:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dst, 1),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=dst_crs,
                resampling=Resampling.bilinear
            )


def compute_slope_deg(dem: np.ndarray, transform) -> np.ndarray:
    """Compute slope in degrees from DEM. Assumes x/y units are meters."""
    xres = float(transform.a)
    yres = abs(float(transform.e))

    dz_dy, dz_dx = np.gradient(dem, yres, xres)
    slope = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
    return slope * (180.0 / np.pi)


def main():

    # 1) Ensure UTM DEM exists
    if not os.path.exists(DEM_UTM):
        print("Reprojecting DEM to UTM35...")
        reproject_dem_to_utm(DEM_IN, DEM_UTM)
        print(f"Saved: {DEM_UTM}")
    else:
        print(f"Using existing: {DEM_UTM}")

    # 2) Read input grid
    print("Loading grid CSV...")
    df = pd.read_csv(GRID_IN)

    # Expect lon/lat columns in degrees
    if "center_lon" not in df.columns or "center_lat" not in df.columns:
        raise ValueError("Input grid must include 'center_lon' and 'center_lat' columns.")

    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df.center_lon, df.center_lat),
        crs="EPSG:4326"
    )

    # 3) Compute slope on UTM DEM
    print("Opening UTM DEM...")
    with rasterio.open(DEM_UTM) as src:
        dem = src.read(1)
        transform = src.transform
        dem_crs = src.crs
        nodata = src.nodata

        print("Computing slope raster...")
        slope = compute_slope_deg(dem, transform)

        # 4) Project points to DEM CRS (UTM) and sample
        print("Projecting grid points to DEM CRS...")
        gdf_utm = gdf.to_crs(dem_crs)

        print("Sampling slope values...")
        slope_vals = []
        for pt in gdf_utm.geometry:
            try:
                row, col = src.index(pt.x, pt.y)
                if 0 <= row < slope.shape[0] and 0 <= col < slope.shape[1]:
                    val = slope[row, col]
                    if nodata is not None and dem[row, col] == nodata:
                        slope_vals.append(np.nan)
                    else:
                        slope_vals.append(float(val))
                else:
                    slope_vals.append(np.nan)
            except Exception:
                slope_vals.append(np.nan)

    df["slope_deg"] = slope_vals

    print("Saving output CSV...")
    df.to_csv(OUT_CSV, index=False)
    print("DONE ✅ slope_deg computed in meters (UTM).")


if __name__ == "__main__":
    main()
