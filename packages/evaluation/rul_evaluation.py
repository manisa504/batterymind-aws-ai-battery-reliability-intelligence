from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _errors(actual: np.ndarray, predicted: np.ndarray) -> dict:
    delta = predicted - actual
    return {
        "mae_ah": float(np.mean(np.abs(delta))),
        "rmse_ah": float(math.sqrt(np.mean(delta**2))),
        "evaluated_points": int(len(actual)),
    }


def evaluate_baselines(cycles: pd.DataFrame, train_fraction: float = 0.6) -> dict:
    discharges = cycles[(cycles.type == "discharge") & cycles.capacity_ah.notna()].copy()
    per_cell: dict[str, dict] = {}
    for battery_id, rows in discharges.groupby("battery_id"):
        rows = rows.sort_values("discharge_cycle_index")
        split = max(5, int(len(rows) * train_fraction))
        training, testing = rows.iloc[:split], rows.iloc[split:]
        x_train = training.discharge_cycle_index.to_numpy(float)
        y_train = training.capacity_ah.to_numpy(float)
        slope, intercept = np.polyfit(x_train, y_train, 1)
        x_test = testing.discharge_cycle_index.to_numpy(float)
        actual = testing.capacity_ah.to_numpy(float)
        linear = slope * x_test + intercept
        persistence = np.repeat(y_train[-1], len(testing))
        per_cell[battery_id] = {
            "training_cutoff_cycle": int(x_train[-1]),
            "first_evaluation_cycle": int(x_test[0]),
            "training_points": int(len(training)),
            "linear": _errors(actual, linear),
            "persistence": _errors(actual, persistence),
        }

    battery_disjoint: dict[str, dict] = {}
    for held_out in sorted(discharges.battery_id.unique()):
        training = discharges[discharges.battery_id != held_out]
        testing = discharges[discharges.battery_id == held_out]
        slope, intercept = np.polyfit(
            training.discharge_cycle_index.to_numpy(float), training.capacity_ah.to_numpy(float), 1
        )
        predicted = slope * testing.discharge_cycle_index.to_numpy(float) + intercept
        battery_disjoint[held_out] = _errors(testing.capacity_ah.to_numpy(float), predicted)

    return {
        "status": "PASS",
        "evaluation_version": "chronological-and-battery-disjoint-v1",
        "train_fraction": train_fraction,
        "future_leakage_control": "Per-cell models fit only rows at or before training_cutoff_cycle.",
        "per_cell_chronological": per_cell,
        "leave_one_battery_out": battery_disjoint,
        "limitations": [
            "Four experimental cells are insufficient to establish broad model generalization.",
            "Leave-one-cell-out capacity-vs-cycle regression does not adjust for operating-profile differences.",
            "Errors describe this dataset and model only; they are not field reliability guarantees.",
        ],
    }
