"""AWS ingestion batch job (ECS Fargate, started by an EventBridge Pipe from the SQS ingestion queue).

Downloads the NASA archive, verifies it against the committed provenance manifest, stores the
unchanged archive in S3 (raw/), runs the same deterministic transformation used locally, uploads the
Parquet outputs and data-quality report (processed/runs/<run_id>/), records whether the outputs are
byte-identical to the committed evidence, and only then promotes them to processed/current/.

Run: python -m packages.ingestion.worker      (request JSON in BATTERYMIND_INGEST_REQUEST)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import time
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from .nasa import ingest_archive, sha256

log = logging.getLogger("batterymind.ingestion")
ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data" / "manifests" / "nasa-source.json"
COMMITTED_REPORT = ROOT / "reports" / "data_quality" / "nasa-ingestion.json"
MAX_ARCHIVE_BYTES = 400 * 1024 * 1024
OUTPUTS = ("cycles", "samples", "impedance")


def _download(url: str, destination: Path) -> int:
    request = urllib.request.Request(url, headers={"User-Agent": "BatteryMind-ingestion/1.0"})
    total = 0
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as out:
        while block := response.read(1024 * 1024):
            total += len(block)
            if total > MAX_ARCHIVE_BYTES:
                raise ValueError("Archive exceeds the expected size bound")
            out.write(block)
    return total


def _exists(s3, bucket: str, key: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as error:
        if error.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def run(request: dict, bucket: str, s3=None) -> dict:
    s3 = s3 or boto3.client("s3")
    manifest = json.loads(MANIFEST.read_text())
    run_id = request.get("run_id") or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    prefix = f"processed/runs/{run_id}"
    status = {"run_id": run_id, "started_utc": datetime.now(UTC).isoformat(), "status": "RUNNING"}
    s3.put_object(Bucket=bucket, Key=f"{prefix}/status.json", Body=json.dumps(status).encode())
    started = time.perf_counter()
    try:
        with tempfile.TemporaryDirectory(prefix="bm-ingest-") as work:
            work_dir = Path(work)
            archive = work_dir / "archive.zip"
            size = _download(manifest["archive_url"], archive)
            digest = sha256(archive)
            hash_matches = digest == manifest["archive_sha256"]
            size_matches = size == manifest["archive_bytes"]
            if not hash_matches or not size_matches:
                raise ValueError(
                    "Archive does not match manifest "
                    f"(sha256_matches={hash_matches}, size_matches={size_matches}, "
                    f"actual_sha256={digest}, actual_bytes={size})"
                )
            raw_key = f"raw/nasa/{digest}.zip"
            if not _exists(s3, bucket, raw_key):
                s3.upload_file(str(archive), bucket, raw_key, ExtraArgs={"Metadata": {"sha256": digest}})
            output_dir = work_dir / "processed"
            report_path = work_dir / "nasa-ingestion.json"
            result = ingest_archive(archive, output_dir, report_path)
            report = json.loads(report_path.read_text())
            committed = json.loads(COMMITTED_REPORT.read_text())["parquet_sha256"]
            matches = {name: report["parquet_sha256"][name] == committed.get(name) for name in OUTPUTS}
            for name in OUTPUTS:
                s3.upload_file(str(output_dir / f"{name}.parquet"), bucket, f"{prefix}/{name}.parquet")
            s3.upload_file(str(report_path), bucket, f"{prefix}/nasa-ingestion.json")
            deterministic = all(matches.values())
            if deterministic:
                for name in OUTPUTS:
                    s3.copy_object(
                        Bucket=bucket,
                        Key=f"processed/current/{name}.parquet",
                        CopySource={"Bucket": bucket, "Key": f"{prefix}/{name}.parquet"},
                    )
            status.update(
                status="PASS" if deterministic else "FAIL",
                finished_utc=datetime.now(UTC).isoformat(),
                duration_s=round(time.perf_counter() - started, 1),
                archive={"sha256": digest, "bytes": size, "s3_key": raw_key},
                rows={"cycles": result.cycles, "samples": result.samples, "impedance": result.impedance_samples},
                parquet_sha256=report["parquet_sha256"],
                matches_committed_evidence=matches,
                promoted_to_current=deterministic,
            )
    except Exception as error:
        status.update(status="FAIL", error=str(error)[:500], finished_utc=datetime.now(UTC).isoformat())
        raise
    finally:
        s3.put_object(Bucket=bucket, Key=f"{prefix}/status.json", Body=json.dumps(status, indent=2).encode())
    return status


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    bucket = os.environ["BATTERYMIND_DATA_BUCKET"]
    raw = os.environ.get("BATTERYMIND_INGEST_REQUEST") or "{}"
    try:
        request = json.loads(raw)
    except json.JSONDecodeError:
        log.error("Ingestion request is not valid JSON")
        return 2
    status = run(request if isinstance(request, dict) else {}, bucket)
    log.info("ingestion %s", json.dumps(status))
    return 0 if status["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
