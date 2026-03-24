# Demand Model

## Purpose
This model computes a `demand` value for every selected fire-risk point.

The goal is to represent how much intervention / response need exists at a point.

---

## Formula

Demand is score-based:

base_demand = min_demand + combined_risk_score * (max_demand - min_demand)

Then controlled random noise is added:

final_demand = round(base_demand + random_noise)

The result is clamped into:

[min_demand, max_demand]

---

## Reproducibility

A `seed` parameter is supported.

If the same:
- input dataset
- selection count
- model parameters
- seed

are used, then:
- selected points are identical
- demand values are identical across runs

---

## Parameters

### min_demand
Minimum demand value.

Default: `1`

### max_demand
Maximum demand value.

Default: `10`

### noise_min
Minimum random noise added to base demand.

Default: `0`

### noise_max
Maximum random noise added to base demand.

Default: `2`

### fallback_high_score
Used when `combined_risk_score` is missing and point risk is HIGH.

Default: `0.85`

### fallback_medium_score
Used when score is missing and point risk is MEDIUM.

Default: `0.60`

### fallback_low_score
Used when score is missing and point risk is LOW.

Default: `0.35`

### fallback_safe_score
Used when score is missing and point risk is SAFE / unknown.

Default: `0.10`

---

## Outputs

Each selected point includes:

- `id`
- `risk_class`
- `center_lat`
- `center_lon`
- `combined_risk_score`
- `demand`

Outputs are generated in:

- CSV
- GeoJSON

---

## Acceptance Criteria Mapping

### 1. Every selected point has a computed demand in CSV and GeoJSON
Satisfied by export logic in `scripts/random_fire_points.py`.

### 2. With the same seed, demand values are identical across runs
Satisfied by:
- `pandas.sample(..., random_state=seed)`
- `Random(seed)` inside `DemandService`

### 3. Model parameters are documented and adjustable
Satisfied by:
- `DemandConfig`
- this document