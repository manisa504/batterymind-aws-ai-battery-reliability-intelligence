from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from packages.evaluation import evaluate_baselines


def main() -> int:
    report = evaluate_baselines(pd.read_parquet("data/processed/cycles.parquet"))
    output = Path("reports/model_evaluation/rul-baselines.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "cells": len(report["per_cell_chronological"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
