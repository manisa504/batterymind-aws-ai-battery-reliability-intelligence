"""Check that regenerated public exports match the committed ones.

Structure, strings, integers and booleans must be identical. Floats must agree to a relative
tolerance of 1e-9: derived regression values (slopes, predictions) differ in the last binary digit
between platforms' numeric libraries, while the measured data is checked byte-for-byte separately
through the Parquet SHA-256 values in reports/data_quality/nasa-ingestion.json.

Usage: python scripts/check_export_reproducible.py <path> [<path> ...]   (compares against git HEAD)
"""

from __future__ import annotations

import json
import math
import subprocess
import sys

REL_TOL = 1e-9


def compare(a, b, where: str, problems: list[str]) -> None:
    if len(problems) >= 20:
        return
    if isinstance(a, bool) or isinstance(b, bool) or not isinstance(a, float | int) or not isinstance(b, float | int):
        if type(a) is not type(b):
            problems.append(f"{where}: type {type(a).__name__} != {type(b).__name__}")
        elif isinstance(a, dict):
            if a.keys() != b.keys():
                problems.append(f"{where}: keys differ {sorted(a.keys() ^ b.keys())[:5]}")
            for key in a.keys() & b.keys():
                compare(a[key], b[key], f"{where}.{key}", problems)
        elif isinstance(a, list):
            if len(a) != len(b):
                problems.append(f"{where}: length {len(a)} != {len(b)}")
            for i, (x, y) in enumerate(zip(a, b, strict=False)):
                compare(x, y, f"{where}[{i}]", problems)
        elif a != b:
            problems.append(f"{where}: {a!r} != {b!r}")
        return
    if isinstance(a, int) and isinstance(b, int):
        if a != b:
            problems.append(f"{where}: {a} != {b}")
    elif not math.isclose(float(a), float(b), rel_tol=REL_TOL, abs_tol=1e-15):
        problems.append(f"{where}: {a!r} != {b!r}")


def main(paths: list[str]) -> int:
    failed = False
    for path in paths:
        committed = json.loads(subprocess.run(["git", "show", f"HEAD:{path}"], check=True, capture_output=True).stdout)
        with open(path) as handle:
            regenerated = json.load(handle)
        problems: list[str] = []
        compare(committed, regenerated, "$", problems)
        print(f"{'OK  ' if not problems else 'FAIL'} {path}")
        for problem in problems:
            print("     ", problem)
        failed = failed or bool(problems)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
