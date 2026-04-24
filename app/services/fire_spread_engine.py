import math
from typing import Dict, List, Optional, Tuple

M_PER_DEG_LAT = 111_320.0


def _meters_to_deg(lat_deg: float, dx_m: float, dy_m: float) -> Tuple[float, float]:
    lat_rad = math.radians(lat_deg)
    m_per_deg_lon = M_PER_DEG_LAT * math.cos(lat_rad)
    dlat = dy_m / M_PER_DEG_LAT
    dlon = dx_m / m_per_deg_lon if m_per_deg_lon != 0 else 0.0
    return dlat, dlon


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def effective_spread_rate_ms(
    wind_speed_ms: float,
    humidity: float = 50.0,
    temperature_c: float = 25.0,
) -> float:
    """
    Effective fire spread rate in m/s.
    Mediterranean scrub fuel model — simplified Rothermel-inspired parameters.
    Typical range: 0.002 m/s (calm, humid) to 0.15 m/s (strong wind, dry, hot).
    """
    base = 0.15  # m/s = 540 m/h in calm conditions (Mediterranean scrub baseline)
    wind_factor = 1.0 + wind_speed_ms * 0.22
    humidity_factor = max(0.08, (100.0 - min(humidity, 100.0)) / 100.0)
    temp_factor = 1.0 + max(0.0, temperature_c - 20.0) * 0.015
    return base * wind_factor * humidity_factor * temp_factor


def compute_spread_polygon(
    center_lat: float,
    center_lon: float,
    wind_dir_deg: float,
    wind_speed_ms: float,
    elapsed_minutes: float,
    humidity: float = 50.0,
    temperature_c: float = 25.0,
    steps: int = 64,
) -> Dict:
    """
    Asymmetric elliptical fire spread polygon after elapsed_minutes.
    Downwind: max spread; upwind: ~12% of front; crosswind: ~50%.
    """
    rate_ms = effective_spread_rate_ms(wind_speed_ms, humidity, temperature_c)
    t_sec = max(elapsed_minutes, 1.0) * 60.0

    front_r = rate_ms * t_sec   # max downwind distance (m)
    back_r = front_r * 0.12
    side_r = front_r * 0.50

    points: List[List[float]] = []
    for i in range(steps + 1):
        theta = (i / steps) * 2 * math.pi
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        if cos_t >= 0:
            r = front_r * cos_t + side_r * abs(sin_t)
        else:
            r = back_r * abs(cos_t) + side_r * abs(sin_t) * 0.4

        bearing_rad = math.radians((wind_dir_deg + math.degrees(theta)) % 360)
        dx = r * math.sin(bearing_rad)
        dy = r * math.cos(bearing_rad)
        dlat, dlon = _meters_to_deg(center_lat, dx, dy)
        points.append([center_lon + dlon, center_lat + dlat])

    if points[0] != points[-1]:
        points.append(points[0])

    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [points]},
        "properties": {
            "model": "koru_ellipse_v1",
            "wind_dir_deg": wind_dir_deg,
            "wind_speed_ms": wind_speed_ms,
            "elapsed_minutes": elapsed_minutes,
            "humidity": humidity,
            "temperature_c": temperature_c,
            "front_radius_km": round(front_r / 1000, 3),
            "spread_rate_ms": round(rate_ms, 5),
        },
    }


def compute_eta(
    fire_lat: float,
    fire_lon: float,
    user_lat: float,
    user_lon: float,
    wind_dir_deg: float,
    wind_speed_ms: float,
    elapsed_minutes: float,
    humidity: float = 50.0,
    temperature_c: float = 25.0,
) -> Optional[float]:
    """
    Returns minutes until fire reaches the user's location.
    0.0  → user already inside spread zone.
    None → fire spreading away, no realistic ETA.
    """
    dist_m = haversine_km(fire_lat, fire_lon, user_lat, user_lon) * 1000

    dlon_r = math.radians(user_lon - fire_lon)
    lat1_r = math.radians(fire_lat)
    lat2_r = math.radians(user_lat)
    x = math.sin(dlon_r) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlon_r)
    bearing = (math.degrees(math.atan2(x, y)) + 360) % 360

    angle_diff = abs((bearing - wind_dir_deg + 180) % 360 - 180)
    rate_ms = effective_spread_rate_ms(wind_speed_ms, humidity, temperature_c)

    cos_f = math.cos(math.radians(angle_diff))
    if cos_f >= 0:
        directional_r = rate_ms * (cos_f * 0.88 + 0.12)
    else:
        # Upwind: minimal spread
        directional_r = rate_ms * (abs(cos_f) * 0.04 + 0.08)

    current_reach_m = directional_r * elapsed_minutes * 60.0

    if dist_m <= current_reach_m:
        return 0.0

    remaining_m = dist_m - current_reach_m
    if directional_r < 1e-6:
        return None

    return remaining_m / directional_r / 60.0
