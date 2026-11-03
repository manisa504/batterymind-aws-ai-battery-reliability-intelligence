from __future__ import annotations

import numpy as np
import pandas as pd

RATED_CAPACITY_AH = 2.0


def capacity_analysis(cycles: pd.DataFrame, battery_id: str, cutoff: int | None = None) -> dict:
    rows = cycles[(cycles["battery_id"] == battery_id) & (cycles["type"] == "discharge")].copy()
    rows = rows.dropna(subset=["capacity_ah", "discharge_cycle_index"])
    if cutoff is not None:
        rows = rows[rows["discharge_cycle_index"] <= cutoff]
    if rows.empty:
        raise ValueError(f"No valid discharge capacity for {battery_id} at the requested cutoff")
    rows = rows.sort_values("discharge_cycle_index")
    x = rows["discharge_cycle_index"].to_numpy(dtype=float)
    y = rows["capacity_ah"].to_numpy(dtype=float)
    slope = float(np.polyfit(x, y, 1)[0]) if len(rows) > 1 else None
    latest = float(y[-1])
    return {
        "battery_id": battery_id,
        "cutoff_cycle": int(x[-1]),
        "latest_capacity_ah": latest,
        "rated_capacity_ah": RATED_CAPACITY_AH,
        "soh_percent": latest / RATED_CAPACITY_AH * 100,
        "degradation_rate_ah_per_cycle": slope,
        "measurements": [
            {
                "cycle": int(cycle),
                "capacity_ah": float(capacity),
                "soh_percent": float(capacity / RATED_CAPACITY_AH * 100),
            }
            for cycle, capacity in zip(x, y, strict=True)
        ],
    }
