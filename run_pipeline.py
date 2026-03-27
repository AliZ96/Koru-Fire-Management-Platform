from pathlib import Path

from summary_generator import generate_summary


def main() -> None:
    csv_path = Path("pipeline_result.csv")
    if not csv_path.exists():
        raise FileNotFoundError(
            "pipeline_result.csv not found in project root. "
            "Place the pipeline output CSV here and run again."
        )

    generate_summary("pipeline_result.csv", "pipeline_summary.json")
    print("pipeline_summary.json generated successfully.")


if __name__ == "__main__":
    main()
