from __future__ import annotations

import random
import time
from typing import Any

from app.services.optimization_service import PIPELINE_RESULT_CSV, _get_coord, get_scenario_info
from app.services.osrm_client import OSRMClient, OSRMError


VEHICLE_CAPACITY = 200


def _route_distance(tour: list[int], station_id: int, distance_by_pair: dict[tuple[int, int], float]) -> float:
    if not tour:
        return 0.0
    nodes = [station_id, *tour, station_id]
    return sum(distance_by_pair.get((nodes[i], nodes[i + 1]), 1_000_000.0) for i in range(len(nodes) - 1))


def _split_by_capacity(ordered_points: list[dict[str, Any]]) -> list[list[int]]:
    vehicles: list[list[int]] = []
    current: list[int] = []
    load = 0
    for point in ordered_points:
        demand = int(point.get("demand") or 0)
        if current and load + demand > VEHICLE_CAPACITY:
            vehicles.append(current)
            current = []
            load = 0
        current.append(int(point["id"]))
        load += demand
    if current:
        vehicles.append(current)
    return vehicles


def _evaluate_order(
    order: list[int],
    points_by_id: dict[int, dict[str, Any]],
    station_id: int,
    distance_by_pair: dict[tuple[int, int], float],
) -> tuple[float, list[list[int]]]:
    vehicles = _split_by_capacity([points_by_id[pid] for pid in order])
    return sum(_route_distance(v, station_id, distance_by_pair) for v in vehicles), vehicles


def _ordered_crossover(parent_a: list[int], parent_b: list[int], rng: random.Random) -> list[int]:
    if len(parent_a) < 2:
        return list(parent_a)
    start, end = sorted(rng.sample(range(len(parent_a)), 2))
    middle = parent_a[start : end + 1]
    rest = [pid for pid in parent_b if pid not in middle]
    return rest[:start] + middle + rest[start:]


def _mutate(order: list[int], rng: random.Random, rate: float = 0.12) -> list[int]:
    mutated = list(order)
    if len(mutated) >= 2 and rng.random() < rate:
        i, j = rng.sample(range(len(mutated)), 2)
        mutated[i], mutated[j] = mutated[j], mutated[i]
    return mutated


def _build_distance_pairs(osrm: OSRMClient, node_ids: list[int]) -> dict[tuple[int, int], float]:
    coords = [(_get_coord(nid)["lat"], _get_coord(nid)["lon"]) for nid in node_ids]
    matrix = osrm.distance_table_km(coords)
    pairs: dict[tuple[int, int], float] = {}
    for i, src in enumerate(node_ids):
        for j, dst in enumerate(node_ids):
            pairs[(src, dst)] = float(matrix[i][j])
    return pairs


def _route_geometry_for_tour(osrm: OSRMClient, tour: list[int], station_id: int) -> tuple[list[list[float]], float, float]:
    nodes = [station_id, *tour, station_id]
    coordinates: list[list[float]] = []
    distance_km = 0.0
    duration_min = 0.0
    for i in range(len(nodes) - 1):
        a = _get_coord(nodes[i])
        b = _get_coord(nodes[i + 1])
        segment = osrm.route_segment(a["lat"], a["lon"], b["lat"], b["lon"])
        segment_coords = segment["coordinates"]
        if coordinates and segment_coords:
            segment_coords = segment_coords[1:]
        coordinates.extend(segment_coords)
        distance_km += segment["distance_km"]
        duration_min += segment["duration_min"]
    return coordinates, distance_km, duration_min


def _optimize_station(
    osrm: OSRMClient,
    station_id: int,
    points: list[dict[str, Any]],
    population_size: int,
    generations: int,
    rng: random.Random,
) -> dict[str, Any]:
    points_by_id = {int(p["id"]): p for p in points}
    point_ids = list(points_by_id)
    distance_by_pair = _build_distance_pairs(osrm, [station_id, *point_ids])

    population: list[list[int]] = [point_ids]
    while len(population) < population_size:
      candidate = list(point_ids)
      rng.shuffle(candidate)
      population.append(candidate)

    best_order = list(point_ids)
    best_cost, best_vehicles = _evaluate_order(best_order, points_by_id, station_id, distance_by_pair)

    for _ in range(generations):
        scored = [
            (*_evaluate_order(candidate, points_by_id, station_id, distance_by_pair), candidate)
            for candidate in population
        ]
        scored.sort(key=lambda item: item[0])
        if scored[0][0] < best_cost:
            best_cost = scored[0][0]
            best_vehicles = scored[0][1]
            best_order = list(scored[0][2])

        elites = [list(item[2]) for item in scored[: max(1, min(3, len(scored)))]]
        next_population = elites[:]
        while len(next_population) < population_size:
            parent_a = list(rng.choice(scored[: max(2, len(scored) // 2)])[2])
            parent_b = list(rng.choice(scored[: max(2, len(scored) // 2)])[2])
            child = _mutate(_ordered_crossover(parent_a, parent_b, rng), rng)
            next_population.append(child)
        population = next_population

    station = _get_coord(station_id)
    vehicles = []
    total_distance = 0.0
    total_duration = 0.0
    for idx, tour in enumerate(best_vehicles):
        geometry, distance_km, duration_min = _route_geometry_for_tour(osrm, tour, station_id)
        total_distance += distance_km
        total_duration += duration_min
        vehicles.append({
            "vehicle_index": idx,
            "tour": [{"node_id": nid, **_get_coord(nid)} for nid in [station_id, *tour, station_id]],
            "polyline": [[lat, lon] for lon, lat in geometry],
            "road_geometry": geometry,
            "load": sum(int(points_by_id[pid].get("demand") or 0) for pid in tour),
            "distance": round(distance_km, 4),
            "duration_min": round(duration_min, 2),
        })

    return {
        "station_id": station_id,
        "station_lat": station.get("lat", 0.0),
        "station_lon": station.get("lon", 0.0),
        "station_name": station.get("name", f"Station {station_id}"),
        "assigned_fire_points": point_ids,
        "total_distance": round(total_distance, 4),
        "total_duration_min": round(total_duration, 2),
        "vehicle_count": len(vehicles),
        "vehicles": vehicles,
        "best_order": best_order,
    }


def run_ga20_road(
    population_size: int = 80,
    generations: int = 80,
    random_seed: int = 42,
    pipeline_points: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if pipeline_points is None and not PIPELINE_RESULT_CSV.exists():
        return {"success": False, "error": "pipeline_result.csv bulunamadı. Önce Pipeline Sonucu çalıştırın."}

    osrm = OSRMClient()
    health = osrm.healthcheck()
    if not health.get("ok"):
        return {
            "success": False,
            "error": "Lokal OSRM çalışmıyor veya erişilemiyor.",
            "detail": health,
        }

    started = time.perf_counter()
    scenario_points = pipeline_points if pipeline_points is not None else get_scenario_info().get("pipeline_points", [])
    grouped: dict[int, list[dict[str, Any]]] = {}
    for point in scenario_points:
        grouped.setdefault(int(point["fire_station_id"]), []).append(point)

    rng = random.Random(random_seed)
    stations = [
        _optimize_station(osrm, station_id, points, population_size, generations, rng)
        for station_id, points in grouped.items()
        if points
    ]
    total_distance = sum(float(s.get("total_distance") or 0.0) for s in stations)
    total_vehicles = sum(int(s.get("vehicle_count") or 0) for s in stations)
    return {
        "success": True,
        "algorithm": "GA20",
        "distance_source": "osrm-road-network",
        "osrm_base_url": osrm.base_url,
        "stations": stations,
        "summary": {
            "total_stations": len(stations),
            "total_vehicles": total_vehicles,
            "total_distance": round(total_distance, 4),
            "total_fire_points": sum(len(s.get("assigned_fire_points", [])) for s in stations),
            "computation_time_ms": round((time.perf_counter() - started) * 1000, 2),
        },
    }
