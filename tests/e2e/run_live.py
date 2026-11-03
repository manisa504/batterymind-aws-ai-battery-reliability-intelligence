"""Live end-to-end test against the deployed AWS stack (real Cognito + MFA, RDS, Bedrock).

Creates two throwaway Cognito users, exercises memory/chat/isolation/restart, writes
reports/performance/live-performance.json, and always deletes the users and their data.
Run:  python tests/e2e/run_live.py
Requires the AWS CLI logged in to the project account and infra/aws-cdk/cdk-outputs.json.
"""

import base64
import hashlib
import hmac
import json
import ssl
import statistics
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import certifi

ROOT = Path(__file__).resolve().parents[2]
OUT = json.loads((ROOT / "infra/aws-cdk/cdk-outputs.json").read_text())["BatteryMindDemo"]
REGION, POOL, CLIENT = "us-east-2", OUT["UserPoolId"], OUT["UserPoolClientId"]
BASE = OUT["ApiUrl"]
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
results: list[dict] = []
latencies: dict[str, list[float]] = {}


def cli(*args):
    r = subprocess.run(["aws", *args, "--region", REGION, "--output", "json"], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"aws {' '.join(args[:2])} failed: {r.stderr[:300]}")
    return json.loads(r.stdout or "{}")


def cognito(*args):
    return cli("cognito-idp", *args)


def totp(secret):
    key = base64.b32decode(secret + "=" * (-len(secret) % 8))
    digest = hmac.new(key, struct.pack(">Q", int(time.time() // 30)), hashlib.sha1).digest()
    offset = digest[-1] & 15
    return f"{(struct.unpack('>I', digest[offset : offset + 4])[0] & 0x7FFFFFFF) % 10**6:06d}"


def create_user():
    username = cognito(
        "admin-create-user",
        "--user-pool-id",
        POOL,
        "--username",
        f"e2e-{uuid.uuid4().hex[:6]}@example.com",
        "--message-action",
        "SUPPRESS",
    )["User"]["Username"]
    password = "Tmp!" + uuid.uuid4().hex[:16] + "Aa1"
    cognito(
        "admin-set-user-password", "--user-pool-id", POOL, "--username", username, "--password", password, "--permanent"
    )

    def login():
        return cognito(
            "initiate-auth",
            "--client-id",
            CLIENT,
            "--auth-flow",
            "USER_PASSWORD_AUTH",
            "--auth-parameters",
            f"USERNAME={username},PASSWORD={password}",
        )

    challenge = login()
    secret = cognito("associate-software-token", "--session", challenge["Session"])
    cognito(
        "verify-software-token",
        "--session",
        secret["Session"],
        "--user-code",
        totp(secret["SecretCode"]),
        "--friendly-device-name",
        "e2e",
    )
    challenge = login()
    time.sleep(31 - time.time() % 30)  # TOTP codes cannot be reused within one 30 s window
    done = cognito(
        "respond-to-auth-challenge",
        "--client-id",
        CLIENT,
        "--challenge-name",
        "SOFTWARE_TOKEN_MFA",
        "--session",
        challenge["Session"],
        "--challenge-responses",
        f"USERNAME={username},SOFTWARE_TOKEN_MFA_CODE={totp(secret['SecretCode'])}",
    )
    return username, done["AuthenticationResult"]["IdToken"]


def call(method, path, token=None, body=None, label=None):
    request = urllib.request.Request(
        BASE + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"content-type": "application/json", **({"authorization": f"Bearer {token}"} if token else {})},
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=90, context=SSL_CONTEXT) as response:
            status, payload = response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        status, payload = error.code, error.read()[:200].decode()
    if label:
        latencies.setdefault(label, []).append((time.perf_counter() - started) * 1000)
    return status, payload


def check(name, condition, detail=""):
    results.append({"check": name, "status": "PASS" if condition else "FAIL", "detail": str(detail)[:240]})
    print(("PASS " if condition else "FAIL ") + name, str(detail)[:140])


def wait_for_stable_service():
    cluster = cli("ecs", "list-clusters")["clusterArns"][0]
    service = cli("ecs", "list-services", "--cluster", cluster)["serviceArns"][0]
    cli("ecs", "update-service", "--cluster", cluster, "--service", service, "--force-new-deployment")
    for _ in range(60):
        time.sleep(10)
        deployments = cli("ecs", "describe-services", "--cluster", cluster, "--services", service)["services"][0][
            "deployments"
        ]
        if len(deployments) == 1 and deployments[0]["runningCount"] == deployments[0]["desiredCount"] >= 1:
            time.sleep(15)
            return True
    return False


users = []
try:
    (name_a, tok_a), (name_b, tok_b) = create_user(), create_user()
    users = [name_a, name_b]
    check("Cognito login with enforced MFA for two users", bool(tok_a and tok_b))

    status, sess = call("POST", "/sessions", tok_a, {"battery_id": "B0005", "objective": "E2E"}, "create_session")
    check("session created", status == 201, status)
    ids = []
    for cutoff in (40, 120):
        status, rec = call(
            "POST",
            "/assessments",
            tok_a,
            {
                "session_id": sess["id"],
                "battery_id": "B0005",
                "cutoff_cycle": cutoff,
                "idempotency_key": f"e2e-{uuid.uuid4().hex}",
            },
            "assessment_with_bedrock_and_embedding",
        )
        ids.append(rec.get("id"))
        check(
            f"assessment at cycle {cutoff} stored with Bedrock explanation",
            status == 201 and bool(rec.get("explanation_source")),
            rec.get("explanation", rec)[:100] if isinstance(rec, dict) else rec,
        )

    status, chat1 = call(
        "POST",
        "/chat",
        tok_a,
        {
            "session_id": sess["id"],
            "cutoff_cycle": 120,
            "message": "How does my earlier assessment compare with the current state of this cell?",
        },
        "chat",
    )
    ok = status == 200 and chat1["context"]["prior_assessments_included"] >= 1
    check("chat recalls prior assessments (semantic + recency)", ok, chat1.get("context") if status == 200 else chat1)
    check(
        "chat found semantic hits in pgvector",
        status == 200 and chat1["context"]["semantic_hits"] >= 1,
        chat1["context"]["semantic_hits"] if status == 200 else "",
    )
    check(
        "context compressed within budget", status == 200 and chat1["context"]["characters_after_compression"] <= 5000
    )
    print("   answer:", chat1.get("answer", "")[:300] if status == 200 else "")
    status, chat2 = call(
        "POST",
        "/chat",
        tok_a,
        {"session_id": sess["id"], "cutoff_cycle": 120, "message": "And what is the predicted remaining useful life?"},
        "chat",
    )
    check("second turn in same session", status == 200, status)
    status, turns = call("GET", f"/sessions/{sess['id']}/turns", tok_a)
    check(
        "short-term memory persisted four turns",
        status == 200 and len(turns["items"]) == 4,
        len(turns["items"]) if status == 200 else turns,
    )

    status, _ = call("GET", f"/sessions/{sess['id']}/turns", tok_b)
    check("cross-user: other user cannot read turns", status == 404, status)
    status, history_b = call("GET", "/batteries/B0005/history", tok_b)
    check("cross-user: other user sees no assessments", status == 200 and history_b["items"] == [], status)
    status, _ = call("POST", "/chat", tok_b, {"session_id": sess["id"], "message": "hi"})
    check("cross-user: other user cannot chat in the session", status == 404, status)
    status, _ = call("DELETE", f"/assessments/{ids[0]}", tok_b)
    check("cross-user: other user cannot delete assessment", status == 404, status)
    status, _ = call("POST", "/chat", None, {"session_id": sess["id"], "message": "hi"})
    check("anonymous chat rejected", status == 401, status)
    status, _ = call("POST", "/chat", tok_a, {"session_id": sess["id"], "message": "x" * 1001})
    check("oversized message rejected", status == 422, status)

    check("ECS task replaced (container restart)", wait_for_stable_service())
    status, history_a = call("GET", "/batteries/B0005/history", tok_a)
    check("after restart: assessments recalled", status == 200 and len(history_a["items"]) == 2, status)
    status, turns = call("GET", f"/sessions/{sess['id']}/turns", tok_a)
    check("after restart: conversation recalled", status == 200 and len(turns["items"]) == 4, status)
    status, chat3 = call(
        "POST",
        "/chat",
        tok_a,
        {"session_id": sess["id"], "cutoff_cycle": 120, "message": "Remind me what we concluded earlier."},
        "chat",
    )
    check(
        "after restart: chat still recalls memory",
        status == 200 and chat3["context"]["prior_assessments_included"] >= 1,
        status,
    )

    status, _ = call("DELETE", f"/assessments/{ids[0]}", tok_a)
    status2, history_a = call("GET", "/batteries/B0005/history", tok_a)
    check("deletion removes assessment", status == 204 and len(history_a["items"]) == 1, (status, status2))
    status, usage = call("GET", "/usage", tok_a)
    check("usage metrics recorded", status == 200 and usage["assistant_replies"] >= 3, usage)
    call("DELETE", f"/sessions/{sess['id']}", tok_a)
finally:
    for name in users:
        try:
            cognito("admin-delete-user", "--user-pool-id", POOL, "--username", name)
        except SystemExit as error:
            print("cleanup failed:", error)
    print("test users deleted:", len(users))

failed = [r for r in results if r["status"] != "PASS"]
summary = {
    "status": "FAIL" if failed or not results else "PASS",
    "executed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "target": OUT["FrontendUrl"],
    "checks": results,
    "latency_ms": {
        k: {"n": len(v), "median": round(statistics.median(v)), "max": round(max(v))} for k, v in latencies.items()
    },
    "note": "Measured from the test client over the public CloudFront URL; includes network time.",
}
(ROOT / "reports/performance/live-performance.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary["latency_ms"]), summary["status"])
sys.exit(1 if failed else 0)
