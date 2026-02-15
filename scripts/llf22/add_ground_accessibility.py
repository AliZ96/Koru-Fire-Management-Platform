import pandas as pd
import numpy as np

IN_CSV = "scripts/llf22/output/izmir_grid_with_accessibility_inputs_v1.csv"
OUT_CSV = "scripts/llf22/output/izmir_ground_accessibility_v1.csv"

# --- Tunable thresholds (Sprint 6 v1) ---
SLOPE_NO_ACCESS = 40.0
SLOPE_HIGH = 15.0
SLOPE_MED = 25.0

ROAD_HIGH_M = 200.0
ROAD_MED_M = 500.0


def normalize_burnable(x):
    """
    burnable can be 0/1, True/False, '0'/'1', or NaN.
    Treat missing as 1 (unknown -> not blocked) to avoid overly aggressive NO_ACCESS.
    """
    if pd.isna(x):
        return 1
    if isinstance(x, (bool, np.bool_)):
        return int(x)
    try:
        return int(float(x))
    except Exception:
        s = str(x).strip().lower()
        if s in ("true", "yes", "y"):
            return 1
        if s in ("false", "no", "n"):
            return 0
        return 1


def main():
    df = pd.read_csv(IN_CSV)

    required = ["dist_to_road_m", "slope_deg"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # burnable is optional but recommended
    if "burnable" not in df.columns:
        df["burnable"] = 1

    # Ensure numeric
    df["dist_to_road_m"] = pd.to_numeric(df["dist_to_road_m"], errors="coerce")
    df["slope_deg"] = pd.to_numeric(df["slope_deg"], errors="coerce")
    df["burnable_norm"] = df["burnable"].apply(normalize_burnable)

    # Default LOW
    df["ground_access_class"] = "LOW"
    df["ground_access_score"] = 1

    # Handle missing slope/road: keep LOW (conservative but not blocking)
    # Hard blocks
    no_access_mask = (df["burnable_norm"] == 0) | (df["slope_deg"] > SLOPE_NO_ACCESS)
    df.loc[no_access_mask, "ground_access_class"] = "NO_ACCESS"
    df.loc[no_access_mask, "ground_access_score"] = 0

    # HIGH (only where not NO_ACCESS)
    high_mask = (
        ~no_access_mask
        & (df["dist_to_road_m"] <= ROAD_HIGH_M)
        & (df["slope_deg"] <= SLOPE_HIGH)
    )
    df.loc[high_mask, "ground_access_class"] = "HIGH"
    df.loc[high_mask, "ground_access_score"] = 3

    # MEDIUM (only where not NO_ACCESS and not HIGH)
    med_mask = (
        ~no_access_mask
        & ~high_mask
        & (df["dist_to_road_m"] <= ROAD_MED_M)
        & (df["slope_deg"] <= SLOPE_MED)
    )
    df.loc[med_mask, "ground_access_class"] = "MEDIUM"
    df.loc[med_mask, "ground_access_score"] = 2

    # Clean helper column (optional to keep; I remove it for final)
    df.drop(columns=["burnable_norm"], inplace=True)

    # Quick sanity summary (prints to terminal)
    print("Ground accessibility distribution:")
    print(df["ground_access_class"].value_counts(dropna=False))
    print("\nScore distribution:")
    print(df["ground_access_score"].value_counts(dropna=False))

    df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved ✅ {OUT_CSV}")


if __name__ == "__main__":
    main()
