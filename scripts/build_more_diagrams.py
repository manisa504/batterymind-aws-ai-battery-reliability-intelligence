# ruff: noqa: E501
"""Generate the supporting architecture diagrams (draw.io source + SVG + PNG) in DOC/architecture/.

  batterymind-memory.drawio    AI memory and retrieval pipeline (spec section 7)
  batterymind-data.drawio      NASA data ingestion and promotion pipeline
  batterymind-delivery.drawio  CI, deployment and hosting

Every statement is taken from the code: apps/api/chat.py, packages/memory_engine, packages/ingestion/worker.py,
infra/aws-cdk and .github/workflows. Run: python scripts/build_more_diagrams.py
"""

from __future__ import annotations

from pathlib import Path

from drawio_lib import AI, COMPUTE, DATABASE, INTEGRATION, MANAGEMENT, SECURITY, STORAGE, Diagram

OUT = Path(__file__).resolve().parents[1] / "DOC" / "architecture"
STEP, STORE, BAD = "#E8F1FB", "#F2F6E8", "#FDECEA"


def memory() -> Diagram:
    d = Diagram("batterymind-memory", 1700, 940)
    d.text(
        "t",
        30,
        10,
        1640,
        50,
        "<b style='font-size:22px'>BatteryMind — AI memory and retrieval pipeline</b><br>One chat request, from sign-in to stored memory. Structured measurements are always authoritative; vector search only chooses which earlier assessments to recall.",
        13,
    )
    # stores (top and bottom rows)
    d.icon("cognito", 160, 90, "cognito", SECURITY, "Amazon Cognito<br>ID token, MFA", "r")
    d.icon("s3data", 930, 90, "s3", STORAGE, "S3 · promoted Parquet<br>measured capacity, cycles", "r")
    d.icon(
        "rds",
        1330,
        90,
        "rds",
        DATABASE,
        "RDS PostgreSQL + pgvector<br>sessions · assessments · turns · embeddings",
        "r",
    )
    d.icon("bedrock_g", 460, 700, "bedrock", AI, "Amazon Bedrock<br>Gemma 3 12B (chat)", "r")
    d.icon("bedrock_t", 1330, 690, "bedrock", AI, "Amazon Bedrock<br>Titan Text Embeddings V2", "b")
    d.icon("rds2", 100, 700, "rds", DATABASE, "RDS PostgreSQL<br>row-level security", "r")
    # row 1
    steps1 = [
        (
            "s1",
            40,
            "1 · Authenticate and authorize",
            "The API verifies the Cognito ID token signature, issuer, audience and expiry. The user id scopes every query.",
        ),
        (
            "s2",
            440,
            "2 · Resolve battery and session",
            "The session must belong to this user and to the requested battery; otherwise the request is refused (404).",
        ),
        (
            "s3",
            840,
            "3 · Retrieve authoritative evidence",
            "Measured discharge capacity, derived SOH, deterministic decision and RUL come from structured data at the chosen cycle cutoff.",
        ),
        (
            "s4",
            1240,
            "4 · Recall prior assessments",
            "Embed the question, then pgvector cosine search over this user's valid assessments for the battery up to the cutoff (top 8), plus the 5 most recent.",
        ),
    ]
    for cid, x, title, body in steps1:
        d.box(cid, x, 250, 340, 150, f"<b>{title}</b><br><br>{body}", STEP)
    steps2 = [
        (
            "s5",
            1240,
            "5 · Rank",
            "score = 0.45 relevance + 0.25 recency + 0.20 importance + 0.10 confidence. Importance follows the decision severity.",
        ),
        (
            "s6",
            840,
            "6 · Compress to budget",
            "Evidence is kept in full; ranked memories are added until a 5,000-character context budget is reached.",
        ),
        (
            "s7",
            440,
            "7 · Generate",
            "Gemma 3 12B answers from the evidence block and the last 6 turns. Rules: label values measured, derived or predicted; cite assessment ids; refuse to invent numbers.",
        ),
        (
            "s8",
            40,
            "8 · Store",
            "Both turns are saved with model id, token counts and latency. New assessments are saved with their embedding for later recall.",
        ),
    ]
    for cid, x, title, body in steps2:
        d.box(cid, x, 480, 340, 150, f"<b>{title}</b><br><br>{body}", STEP)
    d.edge("e12", "s1", "s2", exit_=(1, 0.5), entry=(0, 0.5))
    d.edge("e23", "s2", "s3", exit_=(1, 0.5), entry=(0, 0.5))
    d.edge("e34", "s3", "s4", exit_=(1, 0.5), entry=(0, 0.5))
    d.edge("e45", "s4", "s5", exit_=(0.5, 1), entry=(0.5, 0))
    d.edge("e56", "s5", "s6", exit_=(0, 0.5), entry=(1, 0.5))
    d.edge("e67", "s6", "s7", exit_=(0, 0.5), entry=(1, 0.5))
    d.edge("e78", "s7", "s8", exit_=(0, 0.5), entry=(1, 0.5))
    # store links
    d.edge("c1", "cognito", "s1", dashed=True, exit_=(0.5, 1), entry=(0.5, 0))
    d.edge("m3", "s3data", "s3", dashed=True, exit_=(0.5, 1), entry=(0.5, 0))
    d.edge("r2", "rds", "s4", dashed=True, exit_=(0.5, 1), entry=(0.75, 0))
    d.edge("b4", "s4", "bedrock_t", dashed=True, exit_=(1, 0.5), entry=(1, 0.5), points=[(1650, 325), (1650, 722)])
    d.edge("b7", "s7", "bedrock_g", dashed=True, exit_=(0.5, 1), entry=(0.5, 0))
    d.edge("r8", "s8", "rds2", dashed=True, exit_=(0.5, 1), entry=(0.5, 0))
    # S3 links into step 3 (icon sits above step 3)
    d.group("g_mem", 30, 800, 1640, 125, "Three kinds of memory")
    d.text(
        "mem",
        40,
        828,
        1620,
        90,
        "<b>Short-term</b> — the last 6 chat turns of the session (chat_turns). <b>Episodic</b> — saved assessments with the cutoff, decision, policy version, evidence and validity (valid, superseded or deleted). <b>Semantic</b> — a 1,024-dimension Titan embedding per assessment in pgvector. <b>Authoritative data</b> — NASA measurements and calculated metrics in structured storage, never replaced by retrieved text. Per-user isolation is enforced twice: query filters and forced row-level security through a non-bypass database role.",
        12,
    )
    return d


def data() -> Diagram:
    d = Diagram("batterymind-data", 1900, 820)
    d.text(
        "t",
        30,
        10,
        1840,
        50,
        "<b style='font-size:22px'>BatteryMind — data ingestion and promotion pipeline</b><br>Real NASA Ames measurements are verified, transformed deterministically, and promoted only when they reproduce the committed evidence.",
        13,
    )
    d.box(
        "nasa",
        40,
        120,
        260,
        90,
        "<b>NASA Ames archive</b><br>public S3 object, 209,668,106 bytes. Cells B0005, B0006, B0007, B0018.",
        "#FFFFFF",
    )
    d.box(
        "op", 340, 120, 230, 90, "<b>Operator</b><br>sends a versioned ingestion request as an SQS message.", "#FFFFFF"
    )
    d.icon("sqs", 650, 130, "sqs", INTEGRATION, "Amazon SQS + DLQ<br>3 receives, then dead-letter", "b")
    d.icon("pipe", 900, 130, "eventbridge_pipes", INTEGRATION, "EventBridge Pipe<br>batch size 1", "b")
    d.icon("task", 1150, 130, "fargate", COMPUTE, "ECS Fargate task<br>2 vCPU · 8 GB · ARM64", "b")
    d.icon("s3", 1500, 130, "s3", STORAGE, "S3 data bucket<br>encrypted, TLS only", "b")
    d.edge("a1", "op", "sqs", exit_=(1, 0.5), entry=(0, 0.5))
    d.edge("a2", "sqs", "pipe", exit_=(1, 0.5), entry=(0, 0.5))
    d.edge("a3", "pipe", "task", exit_=(1, 0.5), entry=(0, 0.5))
    d.edge("a4", "task", "s3", exit_=(1, 0.5), entry=(0, 0.5))
    d.edge("a0", "nasa", "task", dashed=True, exit_=(0.5, 0), entry=(0.5, 0), points=[(170, 70), (1182, 70)])
    d.group("g_steps", 30, 300, 1840, 250, "Inside the ingestion task (packages/ingestion/worker.py)")
    steps = [
        (
            "p1",
            "1 · Download and verify",
            "Fetch the archive (size-bounded) and compare SHA-256 and byte count with data/manifests/nasa-source.json. A mismatch fails the run.",
        ),
        (
            "p2",
            "2 · Preserve the original",
            "Store the unchanged archive at raw/nasa/&lt;sha256&gt;.zip. Original laboratory files are never modified.",
        ),
        (
            "p3",
            "3 · Parse and transform",
            "Read the MATLAB cells and write deterministic Parquet: cycles, samples, impedance, plus a data-quality report. Nothing is filled or simulated.",
        ),
        (
            "p4",
            "4 · Compare with evidence",
            "Compare each output hash with reports/data_quality/nasa-ingestion.json, which is committed to Git.",
        ),
        (
            "p5",
            "5 · Promote or refuse",
            "If every hash matches, copy to processed/current/. Otherwise the run is marked FAIL and nothing is promoted. Status is written to processed/runs/&lt;run_id&gt;/status.json.",
        ),
    ]
    for i, (cid, title, body) in enumerate(steps):
        d.box(cid, 50 + i * 365, 340, 340, 190, f"<b>{title}</b><br><br>{body}", "#E8F1FB")
    for a, b in zip(("p1", "p2", "p3", "p4"), ("p2", "p3", "p4", "p5"), strict=True):
        d.edge(f"{a}{b}", a, b, exit_=(1, 0.5), entry=(0, 0.5))
    d.group("g_use", 30, 600, 1840, 200, "What consumes the data")
    d.box(
        "api",
        50,
        650,
        520,
        130,
        "<b>FastAPI service</b><br>On startup it loads processed/current/cycles.parquet from S3 (falling back to the copy baked into the image) and serves analytics: capacity, SOH, RUL baseline, decision.",
        STORE,
    )
    d.box(
        "export",
        620,
        650,
        520,
        130,
        "<b>Showcase export</b> (scripts/export_showcase.py)<br>Builds the versioned JSON from the same Parquet. CI regenerates it and requires the derived values to match within 1e-9.",
        STORE,
    )
    d.box(
        "ci",
        1190,
        650,
        640,
        130,
        "<b>Continuous integration</b><br>Downloads the real archive, verifies the recorded SHA-256, re-runs ingestion, and fails if the Parquet hashes differ from the committed report. Raw data and Parquet are never committed.",
        STORE,
    )
    d.edge("u1", "p5", "api", dashed=True, exit_=(0.5, 1), entry=(0.5, 0), points=[(1580, 580), (310, 580)])
    d.edge("u2", "p5", "export", dashed=True, exit_=(0.5, 1), entry=(0.5, 0), points=[(1580, 580), (880, 580)])
    d.edge("u3", "p5", "ci", dashed=True, exit_=(0.5, 1), entry=(0.5, 0), points=[(1580, 580), (1510, 580)])
    return d


def delivery() -> Diagram:
    d = Diagram("batterymind-delivery", 1900, 810)
    d.text(
        "t",
        30,
        10,
        1840,
        50,
        "<b style='font-size:22px'>BatteryMind — build, deployment and hosting</b><br>Every release path is reviewed and reproducible. The AWS stack is deployed on demand and torn down afterward to avoid charges.",
        13,
    )
    d.box("dev", 40, 130, 220, 90, "<b>Manisha / agent</b><br>commits to GitHub (main).", "#FFFFFF")
    d.box("gh", 330, 130, 260, 90, "<b>GitHub repository</b><br>public; no raw data, credentials or caches.", "#FFFFFF")
    d.edge("g1", "dev", "gh", exit_=(1, 0.5), entry=(0, 0.5))
    d.group("g_ci", 660, 90, 1210, 190, "GitHub Actions · CI on every push and pull request")
    ci = [
        ("c1", "Static checks", "ruff lint and format; docs page in sync with gate files and reports."),
        (
            "c2",
            "Tests",
            "Unit, security, API and memory tests; PostgreSQL + pgvector tests in a container; CDK assertions.",
        ),
        (
            "c3",
            "Real-data reproducibility",
            "Download the NASA archive, verify SHA-256, re-run ingestion and the exports.",
        ),
        ("c4", "Build and browser test", "Build the app and showcase; drive the built showcase in headless Chrome."),
    ]
    for i, (cid, title, body) in enumerate(ci):
        d.box(cid, 680 + i * 295, 130, 280, 135, f"<b>{title}</b><br><br>{body}", "#E8F1FB")
    d.edge("g2", "gh", "g_ci", exit_=(1, 0.5), entry=(0, 0.5))
    d.group("g_deploy", 30, 340, 1840, 250, "Deployment targets")
    d.box(
        "manual",
        50,
        390,
        300,
        170,
        "<b>AWS (manual, reviewed)</b><br>Operator runs <i>cdk diff</i>, reviews it, then <i>cdk deploy</i>. The GitHub OIDC deploy role is blocked by an AWS Organizations policy, so the deploy workflow cannot run.",
        "#FDF3E1",
        "#ED7100",
    )
    d.icon("cfn", 420, 400, "cloudformation", MANAGEMENT, "AWS CloudFormation<br>stack BatteryMindDemo", "b")
    d.icon("ecr", 650, 400, "ecr", COMPUTE, "Amazon ECR<br>immutable ARM64 tags", "b")
    d.icon("fargate", 880, 400, "fargate", COMPUTE, "ECS Fargate<br>API and ingestion", "b")
    d.box(
        "vercel",
        1130,
        390,
        360,
        80,
        "<b>Vercel</b> · batterymind-app<br>React chat app, calls the AWS API when it is running. Deployed with the Vercel CLI.",
        "#FFFFFF",
    )
    d.box(
        "vercel2",
        1130,
        490,
        360,
        70,
        "<b>Vercel</b> · batterymind-showcase<br>static export, never depends on AWS.",
        "#FFFFFF",
    )
    d.box(
        "pages",
        1530,
        390,
        320,
        170,
        "<b>GitHub Pages</b><br>explainer page, architecture diagrams and video from DOC/. Published by a manually dispatched workflow.",
        "#FFFFFF",
    )
    d.edge("d1", "manual", "cfn", exit_=(1, 0.5), entry=(0, 0.5))
    d.edge("d2", "cfn", "ecr", exit_=(1, 0.5), entry=(0, 0.5))
    d.edge("d3", "ecr", "fargate", exit_=(1, 0.5), entry=(0, 0.5))
    d.edge("h1", "gh", "manual", dashed=True, exit_=(0.5, 1), entry=(0.5, 0), points=[(460, 310), (200, 310)])
    d.edge("h2", "gh", "pages", dashed=True, exit_=(0.5, 1), entry=(0.5, 0), points=[(460, 322), (1690, 322)])
    d.group("g_state", 30, 650, 1840, 140, "Release state and cost control")
    d.text(
        "state",
        50,
        680,
        1800,
        100,
        "<b>Validated</b>: image v14 on AWS us-east-2 — live suite 24 of 24 checks, 4 of 4 X-Ray traces, Fargate ingestion matching committed evidence. <b>Torn down</b> on 2026-11-06 to remove charges; checks found no remaining stack, bucket, repository, user pool, database, snapshot, load balancer or log group. <b>Always available at no cost</b>: GitHub, GitHub Pages and both Vercel sites. <b>Reprovisioning</b> follows docs/runbooks/deployment.md and requires Manisha's authorization; the CDK pins Region us-east-2 and in-region Bedrock models only. <b>Cost</b>: an 8-hour demonstration is estimated at $2.95 of fixed charges and about $60.80 per month if left running (reports/cost).",
        12,
    )
    return d


if __name__ == "__main__":
    for build in (memory, data, delivery):
        build().save(OUT)
