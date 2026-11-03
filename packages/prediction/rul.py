from __future__ import annotations

import numpy as np


def estimate_linear_rul(cycles: list[int], capacities: list[float], threshold_ah: float = 1.4) -> dict:
    if len(cycles) < 5 or len(cycles) != len(capacities):
        return {"status": "unavailable", "reason": "At least five aligned measurements are required."}
    x = np.asarray(cycles, dtype=float)
    y = np.asarray(capacities, dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    if slope >= 0:
        return {"status": "unavailable", "reason": "A decreasing capacity trend was not observed."}
    crossing = (threshold_ah - intercept) / slope
    remaining = max(0.0, crossing - x[-1])
    residuals = y - (slope * x + intercept)
    rng = np.random.default_rng(20261102)
    crossings = []
    for _ in range(500):
        sampled = rng.choice(residuals, size=len(residuals), replace=True)
        boot_slope, boot_intercept = np.polyfit(x, slope * x + intercept + sampled, 1)
        if boot_slope < 0:
            crossings.append(max(0.0, (threshold_ah - boot_intercept) / boot_slope - x[-1]))
    interval = np.quantile(crossings, [0.05, 0.95]).tolist() if crossings else [None, None]
    return {
        "status": "available",
        "model_version": "linear-residual-bootstrap-v1",
        "threshold_ah": threshold_ah,
        "estimated_remaining_cycles": remaining,
        "interval_90_cycles": interval,
        "slope_ah_per_cycle": float(slope),
        "prediction_kind": "model_prediction",
    }
