from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from packages.battery_analytics import capacity_analysis
from packages.decision_engine import classify
from packages.prediction import estimate_linear_rul


def main() -> int:
    cycles = pd.read_parquet("data/processed/cycles.parquet")
    samples = pd.read_parquet(
        "data/processed/samples.parquet",
        columns=[
            "battery_id",
            "source_cycle_index",
            "sample_index",
            "elapsed_seconds",
            "voltage_measured_v",
            "temperature_measured_c",
        ],
    )
    batteries = []
    for battery_id in sorted(cycles.battery_id.unique()):
        analysis = capacity_analysis(cycles, battery_id)
        analysis["classification"] = classify(analysis["soh_percent"], len(analysis["measurements"])).__dict__
        analysis["rul"] = estimate_linear_rul(
            [row["cycle"] for row in analysis["measurements"]], [row["capacity_ah"] for row in analysis["measurements"]]
        )
        discharge_cycles = cycles[(cycles.battery_id == battery_id) & (cycles.type == "discharge")][
            ["source_cycle_index", "discharge_cycle_index"]
        ]
        profile_rows = samples[samples.battery_id == battery_id].merge(discharge_cycles, on="source_cycle_index")
        profiles = []
        for cycle, rows in profile_rows.groupby("discharge_cycle_index", sort=True):
            rows = rows.sort_values("sample_index")
            stride = max(1, len(rows) // 40)
            selected = rows.iloc[::stride]
            if selected.index[-1] != rows.index[-1]:
                selected = pd.concat([selected, rows.iloc[[-1]]])
            profiles.append(
                {
                    "cycle": int(cycle),
                    "samples": [
                        {
                            "elapsed_seconds": round(float(row.elapsed_seconds), 3),
                            "voltage_v": round(float(row.voltage_measured_v), 5),
                            "temperature_c": round(float(row.temperature_measured_c), 4),
                        }
                        for row in selected.itertuples()
                    ],
                }
            )
        analysis["discharge_profiles"] = profiles
        batteries.append(analysis)
    payload = {
        "schema_version": "1.1.0",
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
