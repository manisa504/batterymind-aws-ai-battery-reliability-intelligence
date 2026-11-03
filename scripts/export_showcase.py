from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from packages.battery_analytics import capacity_analysis
from packages.decision_engine import classify
from packages.prediction import estimate_linear_rul


def main() -> int:
    cycles = pd.read_parquet("data/processed/cycles.parquet")
    batteries = []
    for battery_id in sorted(cycles.battery_id.unique()):
        analysis = capacity_analysis(cycles, battery_id)
        analysis["classification"] = classify(analysis["soh_percent"], len(analysis["measurements"])).__dict__
        analysis["rul"] = estimate_linear_rul(
            [row["cycle"] for row in analysis["measurements"]], [row["capacity_ah"] for row in analysis["measurements"]]
        )
        batteries.append(analysis)
    payload = {
        "schema_version": "1.0.0",
        "source_manifest": "data/manifests/nasa-source.json",
        "generated_from": "data/processed/cycles.parquet",
        "batteries": batteries,
    }
    destinations = [Path("showcase/public/data/batteries.v1.json"), Path("apps/web/public/data/batteries.v1.json")]
    for destination in destinations:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"batteries": len(batteries), "destinations": [str(x) for x in destinations]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
