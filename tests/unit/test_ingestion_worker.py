import json
from types import SimpleNamespace

from botocore.exceptions import ClientError

from packages.ingestion import worker


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.copies = []

    def put_object(self, *, Bucket, Key, Body, **kwargs):
        self.objects[(Bucket, Key)] = Body

    def head_object(self, *, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise ClientError({"Error": {"Code": "404", "Message": "missing"}}, "HeadObject")
        return {}

    def upload_file(self, filename, bucket, key, ExtraArgs=None):
        with open(filename, "rb") as stream:
            self.objects[(bucket, key)] = stream.read()

    def copy_object(self, *, Bucket, Key, CopySource):
        self.copies.append((Bucket, Key, CopySource))
        self.objects[(Bucket, Key)] = self.objects[(CopySource["Bucket"], CopySource["Key"])]


def configure_run(monkeypatch, tmp_path, hashes):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"archive_url": "https://example.invalid/archive.zip", "archive_sha256": "ok", "archive_bytes": 7})
    )
    report = tmp_path / "committed.json"
    report.write_text(json.dumps({"parquet_sha256": hashes}))
    monkeypatch.setattr(worker, "MANIFEST", manifest)
    monkeypatch.setattr(worker, "COMMITTED_REPORT", report)
    monkeypatch.setattr(worker, "_download", lambda _url, destination: destination.write_bytes(b"archive") or 7)
    monkeypatch.setattr(worker, "sha256", lambda _path: "ok")

    def ingest(_archive, output_dir, report_path):
        output_dir.mkdir()
        for name in worker.OUTPUTS:
            (output_dir / f"{name}.parquet").write_bytes(name.encode())
        report_path.write_text(json.dumps({"parquet_sha256": hashes}))
        return SimpleNamespace(cycles=2167, samples=2089050, impedance_samples=42576)

    monkeypatch.setattr(worker, "ingest_archive", ingest)


def test_matching_outputs_are_promoted(monkeypatch, tmp_path):
    hashes = {name: f"{name}-hash" for name in worker.OUTPUTS}
    configure_run(monkeypatch, tmp_path, hashes)
    s3 = FakeS3()

    result = worker.run({"run_id": "unit-pass"}, "bucket", s3)

    assert result["status"] == "PASS"
    assert result["promoted_to_current"] is True
    assert len(s3.copies) == 3
    status = json.loads(s3.objects[("bucket", "processed/runs/unit-pass/status.json")])
    assert status["rows"]["samples"] == 2089050


def test_mismatched_output_is_not_promoted(monkeypatch, tmp_path):
    produced = {name: f"{name}-hash" for name in worker.OUTPUTS}
    configure_run(monkeypatch, tmp_path, {**produced, "cycles": "expected-other"})

    def ingest(_archive, output_dir, report_path):
        output_dir.mkdir()
        for name in worker.OUTPUTS:
            (output_dir / f"{name}.parquet").write_bytes(name.encode())
        report_path.write_text(json.dumps({"parquet_sha256": produced}))
        return SimpleNamespace(cycles=2167, samples=2089050, impedance_samples=42576)

    monkeypatch.setattr(worker, "ingest_archive", ingest)
    s3 = FakeS3()

    result = worker.run({"run_id": "unit-fail"}, "bucket", s3)

    assert result["status"] == "FAIL"
    assert result["promoted_to_current"] is False
    assert s3.copies == []
