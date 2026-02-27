# Accessibility Classification v1 (SCRUM-57)

## Output Schema (v1)
Each risk zone row includes:
- ground_access_class_v1: LOW | MEDIUM | HIGH  (difficulty level; HIGH = harder)
- ground_access_score_v1: 1 | 2 | 3
- air_access_class_v1: LOW | MEDIUM | HIGH
- air_access_score_v1: 1 | 2 | 3
- road_dist_class: NEAR | MID | FAR | UNKNOWN
- slope_class: LOW | MEDIUM | HIGH | UNKNOWN
- ground_reason_v1, air_reason_v1 (explanations)

## Ground Rules (v1)
Inputs:
- dist_to_road_m
- slope_deg

Road score:
- dist_to_road_m <= 250m  -> 1 (NEAR)
- 250m < dist_to_road_m <= 1000m -> 2 (MID)
- dist_to_road_m > 1000m -> 3 (FAR)
- missing -> 3 (UNKNOWN)

Slope score:
- slope_deg <= 10°  -> 1 (LOW)
- 10° < slope_deg <= 20° -> 2 (MEDIUM)
- slope_deg > 20° -> 3 (HIGH)
- missing -> 2 (UNKNOWN, conservative)

Ground:
- ground_access_score_v1 = max(road_score, slope_score)
- score -> class mapping:
  - 1 => LOW difficulty
  - 2 => MEDIUM difficulty
  - 3 => HIGH difficulty

## Air Rules (v1)
Since landing zone / air-base data is not included in this dataset, air accessibility is slope-based in v1:
- air_access_score_v1 = slope_score
- score -> class mapping as above

## Coverage Check (Done Evidence)
Run:
python scripts/llf22/accessibility/classify_accessibility_v1.py --input data/raw/izmir_ground_accessibility_v1.csv --output data/outputs/accessibility_labels_v1.csv --geojson data/outputs/accessibility_layer_v1.geojson

Result:
- rows_total: 2075
- ground_class_empty: 0
- air_class_empty: 0
- ground_score_unique: [1, 2, 3]
- air_score_unique: [1, 2, 3]