import math
from typing import Dict, List

M_PER_DEG_LAT = 111_320.0  # ~ metre/deg

def meters_to_deg(lat_deg: float, dx_m: float, dy_m: float):
    lat_rad = math.radians(lat_deg)
    m_per_deg_lon = M_PER_DEG_LAT * math.cos(lat_rad)
    dlat = dy_m / M_PER_DEG_LAT
    dlon = dx_m / m_per_deg_lon if m_per_deg_lon != 0 else 0.0
    return dlat, dlon

def make_spread_sector(center_lat: float, center_lon: float,
                       wind_dir_deg: float, wind_speed_ms: float,
                       duration_min: float = 30.0,
                       half_angle_deg: float = 25.0,
                       elongation: float = 2.0,
                       steps: int = 36) -> Dict:
    t_sec = max(duration_min, 1.0) * 60.0
    base_r = max(wind_speed_ms, 0.5) * t_sec * 0.5  # demo ölçek

    points: List[List[float]] = []
    start = wind_dir_deg - half_angle_deg
    end = wind_dir_deg + half_angle_deg
    step = (end - start) / steps

    for i in range(steps + 1):
        ang = math.radians(start + i * step)
        w = (1.0 + elongation * max(0.0, math.cos(ang - math.radians(wind_dir_deg))))
        r = base_r * (0.6 + 0.4 * w)
        dx = r * math.sin(ang)
        dy = r * math.cos(ang)
        dlat, dlon = meters_to_deg(center_lat, dx, dy)
        points.append([center_lon + dlon, center_lat + dlat])

    back_r = base_r * 0.2
    for i in range(steps, -1, -1):
        ang = math.radians(start + i * step)
        dx = back_r * math.sin(ang)
        dy = back_r * math.cos(ang)
        dlat, dlon = meters_to_deg(center_lat, dx, dy)
        points.append([center_lon + dlon, center_lat + dlat])

    if points and points[0] != points[-1]:
        points.append(points[0])

    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [points]},
        "properties": {
            "model": "naive_wind_sector",
            "wind_dir": wind_dir_deg,
            "wind_speed_ms": wind_speed_ms,
            "duration_min": duration_min,
        },
    }
