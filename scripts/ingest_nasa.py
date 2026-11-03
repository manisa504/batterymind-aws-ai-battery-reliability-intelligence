from __future__ import annotations

import argparse
import json
from pathlib import Path

from packages.ingestion import ingest_archive


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and transform NASA battery MATLAB files")
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/processed"))
    args = parser.parse_args()
    result = ingest_archive(args.archive, args.output, Path("reports/data_quality/nasa-ingestion.json"))
    print(
        json.dumps(
            {
                "cells": result.cells,
                "cycles": result.cycles,
                "samples": result.samples,
                "impedance_samples": result.impedance_samples,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
