from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.io import loadmat

TARGET_CELLS = ("B0005", "B0006", "B0007", "B0018")


@dataclass(frozen=True)
class IngestionResult:
    cells: tuple[str, ...]
    cycles: int
    samples: int
    impedance_samples: int
    output_dir: Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _scalar(value: Any) -> Any:
    array = np.asarray(value)
    if array.size == 0:
        return None
    return array.reshape(-1)[0]


def _series(data: Any, name: str) -> np.ndarray:
    value = getattr(data, name, np.array([]))
    return np.asarray(value).reshape(-1)


def _complex_parts(value: Any, index: int) -> tuple[float | None, float | None]:
    values = np.asarray(value).reshape(-1)
    if index >= len(values):
        return None, None
    number = complex(values[index])
    return float(number.real), float(number.imag)


def _timestamp(date_vector: Any) -> str | None:
    values = np.asarray(date_vector).reshape(-1)
    if len(values) < 6:
        return None
    second = float(values[5])
    whole = int(second)
    microsecond = round((second - whole) * 1_000_000)
    return datetime(
        int(values[0]),
        int(values[1]),
        int(values[2]),
        int(values[3]),
        int(values[4]),
        whole,
        microsecond,
    ).isoformat()


def _extract_target_files(archive: Path, destination: Path) -> dict[str, Path]:
    nested = destination / "nested"
    nested.mkdir(parents=True, exist_ok=True)
    found: dict[str, Path] = {}
    with zipfile.ZipFile(archive) as outer:
        nested_name = next(name for name in outer.namelist() if name.endswith("1. BatteryAgingARC-FY08Q4.zip"))
        nested_archive = nested / "source.zip"
        with outer.open(nested_name) as source, nested_archive.open("wb") as target:
            shutil.copyfileobj(source, target)
    with zipfile.ZipFile(nested_archive) as inner:
        names = set(inner.namelist())
        for cell in TARGET_CELLS:
            name = f"{cell}.mat"
            if name not in names:
                raise ValueError(f"Required candidate cell {cell} is absent from verified archive")
            path = destination / name
            with inner.open(name) as source, path.open("wb") as target:
                shutil.copyfileobj(source, target)
            found[cell] = path
    return found


def _parse_cell(battery_id: str, mat_path: Path) -> tuple[list[dict], list[dict], list[dict]]:
    payload = loadmat(mat_path, squeeze_me=True, struct_as_record=False)
    battery = payload[battery_id]
    operations = np.atleast_1d(battery.cycle)
    source_hash = sha256(mat_path)
    cycles: list[dict] = []
    samples: list[dict] = []
    impedance: list[dict] = []
    discharge_index = 0
    for source_index, operation in enumerate(operations):
        operation_type = str(operation.type)
        data = operation.data
        capacity = None
        current_discharge_index = None
        if operation_type == "discharge":
            discharge_index += 1
            current_discharge_index = discharge_index
            capacity_value = _scalar(getattr(data, "Capacity", np.array([])))
            capacity = float(capacity_value) if capacity_value is not None else None
        elapsed = _series(data, "Time")
        voltage = _series(data, "Voltage_measured")
        current = _series(data, "Current_measured")
        temperature = _series(data, "Temperature_measured")
        charger_current = _series(data, "Current_charge")
        charger_voltage = _series(data, "Voltage_charge")
        sample_count = max(map(len, (elapsed, voltage, current, temperature)), default=0)
        flags: list[str] = []
        lengths = {len(x) for x in (elapsed, voltage, current, temperature) if len(x)}
        if len(lengths) > 1:
            flags.append("unequal_measurement_lengths")
        if operation_type == "discharge" and capacity is None:
            flags.append("missing_capacity")
        cycles.append(
            {
                "battery_id": battery_id,
                "source_cycle_index": source_index,
                "type": operation_type,
                "ambient_temperature_c": float(operation.ambient_temperature),
                "experiment_started_at_local": _timestamp(operation.time),
                "discharge_cycle_index": current_discharge_index,
                "capacity_ah": capacity,
                "sample_count": sample_count,
                "source_file_sha256": source_hash,
                "quality_flags": ";".join(flags),
            }
        )
        for index in range(sample_count):

            def at(values: np.ndarray, sample_index: int = index) -> float | None:
                return float(values[sample_index]) if sample_index < len(values) else None

            samples.append(
                {
                    "battery_id": battery_id,
                    "source_cycle_index": source_index,
                    "sample_index": index,
                    "elapsed_seconds": at(elapsed),
                    "voltage_measured_v": at(voltage),
                    "current_measured_a": at(current),
                    "temperature_measured_c": at(temperature),
                    "current_load_or_charge_a": at(charger_current),
                    "voltage_load_or_charge_v": at(charger_voltage),
                    "source_file_sha256": source_hash,
                }
            )
        if operation_type == "impedance":
            fields = ["Sense_current", "Battery_current", "Current_ratio", "Battery_impedance", "Rectified_impedance"]
            impedance_count = max((len(_series(data, field)) for field in fields), default=0)
            for index in range(impedance_count):
                row: dict[str, Any] = {
                    "battery_id": battery_id,
                    "source_cycle_index": source_index,
                    "sample_index": index,
                    "re_ohm": float(_scalar(getattr(data, "Re", np.array([np.nan])))),
                    "rct_ohm": float(_scalar(getattr(data, "Rct", np.array([np.nan])))),
                    "source_file_sha256": source_hash,
                }
                for field in fields:
                    real, imag = _complex_parts(getattr(data, field, np.array([])), index)
                    key = field.lower()
                    row[f"{key}_real"] = real
                    row[f"{key}_imag"] = imag
                impedance.append(row)
    return cycles, samples, impedance


def ingest_archive(archive: Path, output_dir: Path, report_path: Path) -> IngestionResult:
    archive = archive.resolve()
    expected = "82302a7db4fc1b34e0b6676326610438d43b816bdf11a69d1d012a464ef2f92e"
    actual = sha256(archive)
    if actual != expected:
        raise ValueError(f"Archive SHA-256 mismatch: expected {expected}, got {actual}")
    all_cycles: list[dict] = []
    all_samples: list[dict] = []
    all_impedance: list[dict] = []
    file_manifest: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="batterymind-") as temporary:
        files = _extract_target_files(archive, Path(temporary))
        for battery_id, path in sorted(files.items()):
            cycles, samples, impedance = _parse_cell(battery_id, path)
            all_cycles.extend(cycles)
            all_samples.extend(samples)
            all_impedance.extend(impedance)
            file_manifest.append({"battery_id": battery_id, "sha256": sha256(path), "bytes": path.stat().st_size})
    output_dir.mkdir(parents=True, exist_ok=True)
    cycle_frame = pd.DataFrame(all_cycles).sort_values(["battery_id", "source_cycle_index"])
    sample_frame = pd.DataFrame(all_samples).sort_values(["battery_id", "source_cycle_index", "sample_index"])
    impedance_frame = pd.DataFrame(all_impedance).sort_values(["battery_id", "source_cycle_index", "sample_index"])
    paths = {
        "cycles": output_dir / "cycles.parquet",
        "samples": output_dir / "samples.parquet",
        "impedance": output_dir / "impedance.parquet",
    }
    cycle_frame.to_parquet(paths["cycles"], index=False)
    sample_frame.to_parquet(paths["samples"], index=False)
    impedance_frame.to_parquet(paths["impedance"], index=False)

    def numeric_summary(frame: pd.DataFrame, column: str) -> dict:
        values = frame[column]
        return {
            "unit": {
                "capacity_ah": "Ah",
                "voltage_measured_v": "V",
                "current_measured_a": "A",
                "temperature_measured_c": "degC",
                "re_ohm": "ohm",
                "rct_ohm": "ohm",
            }[column],
            "present": int(values.notna().sum()),
            "missing": int(values.isna().sum()),
            "minimum": float(values.min()),
            "maximum": float(values.max()),
            "nonfinite": int((~np.isfinite(values.dropna().to_numpy(float))).sum()),
        }

    measurements = {
        "capacity_ah": numeric_summary(cycle_frame, "capacity_ah"),
        "voltage_measured_v": numeric_summary(sample_frame, "voltage_measured_v"),
        "current_measured_a": numeric_summary(sample_frame, "current_measured_a"),
        "temperature_measured_c": numeric_summary(sample_frame, "temperature_measured_c"),
        "re_ohm": numeric_summary(impedance_frame, "re_ohm"),
        "rct_ohm": numeric_summary(impedance_frame, "rct_ohm"),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "status": "PASS",
                "archive_sha256": actual,
                "source_files": file_manifest,
                "cells": list(TARGET_CELLS),
                "cycle_rows": len(all_cycles),
                "sample_rows": len(all_samples),
                "impedance_rows": len(all_impedance),
                "quality_flags": pd.Series([row["quality_flags"] for row in all_cycles]).value_counts().to_dict(),
                "measurement_validation": measurements,
                "quality_concerns": [
                    "Two sample rows have missing core measured fields due to unequal "
                    "source-array lengths; values were not filled.",
                    "Measured-voltage extrema include values below 0 V and above 5 V; "
                    "source values are preserved and require operation-level interpretation.",
                    "Capacity is defined only for discharge operations, so null capacity on "
                    "charge and impedance rows is expected.",
                    "MATLAB date vectors contain no timezone; timestamps remain timezone-naive.",
                ],
                "missing_experiment_timestamps": int(cycle_frame["experiment_started_at_local"].isna().sum()),
                "parquet_sha256": {name: sha256(path) for name, path in paths.items()},
                "timezone_assigned": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return IngestionResult(TARGET_CELLS, len(all_cycles), len(all_samples), len(all_impedance), output_dir)
