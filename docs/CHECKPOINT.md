# BatteryMind checkpoint — 2026-11-03 (end of day)

Read this first, then `AGENTS.md`. The full requirements are the original Codex system prompt for
BatteryMind (Manisha keeps a copy); gates are tracked in `docs/gates/`.

## State at stop

- **AWS stack `BatteryMindDemo` (us-east-2) was torn down** at Manisha's request to stop charges.
  Retained by design (near-zero cost): RDS final snapshot, S3 data bucket, ECR repository (images
  `release`, `v2`–`v6`), Cognito user pool (0 users). Verify with the commands under "Bring it back".
- **Vercel**
  - `batterymind-showcase` (recruiter showcase, static, no AWS): live at https://batterymind-showcase.vercel.app
  - `batterymind-app` (the real chat app, `apps/web`): deployed at https://batterymind-app.vercel.app but
    **non-functional until AWS is redeployed** (its `config.json` points at the destroyed CloudFront URL).
- **GitHub**: https://github.com/manisa504/batterymind-aws-ai-battery-reliability-intelligence (public).
  `main` holds everything through the live chat assistant. Today's unfinished work is on branch
  `wip/2026-11-03` (see below).
- **GitHub Pages**: not enabled yet. `DOC/index.html` was rewritten (on the WIP branch) with results generated
  from the report files.

## Done and verified (evidence in `reports/`)

- Real NASA data, checksummed; analytics, SOH, linear RUL with chronological evaluation; deterministic policy.
- Evidence-grounded chat (`POST /api/v1/chat`): measurements first, ranked prior assessments (Titan embeddings in
  pgvector + recency + importance), budgeted context, Bedrock `google.gemma-3-12b-it` (on-demand, us-east-2).
- Memory: sessions, assessments, chat turns, deletion; forced RLS applied at startup through role
  `batterymind_app`. Live E2E `tests/e2e/run_live.py`: 21/21 PASS (`reports/performance/live-performance.json`).
- Web app: Cognito PKCE sign-in (MFA required), Assistant, Decision history, Evaluation views.
- CORS for the Vercel app origin verified (allowed origin 200, unknown origin 400); Cognito callback/logout URLs
  include `https://batterymind-app.vercel.app/` (CDK context `appOrigins`).

## In progress on `wip/2026-11-03` (not deployed, not tested)

1. `packages/ingestion/worker.py` — Fargate batch job: download NASA archive, verify SHA-256/size against
   `data/manifests/nasa-source.json`, store raw in `s3://<data>/raw/nasa/<sha>.zip`, run `ingest_archive`, upload
   `processed/runs/<run_id>/`, compare Parquet hashes with `reports/data_quality/nasa-ingestion.json`, promote to
   `processed/current/` only if identical. **Still to do:**
   - CDK: `IngestionTask` (ARM64, ~2 vCPU / 8 GB, same image, command `python -m packages.ingestion.worker`,
     public subnet + public IP because there is no NAT), task role read/write on the data bucket.
   - CDK: EventBridge Pipe (`aws_pipes.CfnPipe`) SQS `IngestionQueue` → ECS RunTask, batch size 1, container
     override env `BATTERYMIND_INGEST_REQUEST=$.body`; pipe role needs sqs receive/delete, `ecs:RunTask`,
     `iam:PassRole` for task + execution roles.
   - `scripts/run_ingestion_aws.sh` to send the SQS message (operator action; no public admin API).
   - API: load `processed/current/cycles.parquet` from S3 at startup when present, else the baked copy; report
     the data source in `/api/v1/batteries`.
   - Unit tests for `worker.run` with a stubbed S3 client; live run evidence into `reports/`.
2. `scripts/build_architecture_diagram.py` — official aws4 icons/groups. **Do this last** (Manisha's instruction).
   Correct it first: API tasks run in **public** subnets with public IPs (there is no private app subnet);
   RDS is in isolated subnets.
3. `DOC/index.html` updates, `DOC/architecture/*` label fixes, `scripts/publish_vercel_app.sh`.

## Remaining work, in Manisha's agreed order

1. Ingestion on AWS (above).
2. App views per spec §9: Analysis needs temperature/voltage charts, measured vs predicted trajectory, RUL with
   uncertainty (check what exists first); Evaluation needs operating cost.
3. Memory per spec §7: user-confirmed actions, confirmed preferences; tests for recall across two sessions,
   live correction/supersession, live concurrent updates, browser restart.
4. Observability: CloudWatch alarms (5xx, task count, RDS CPU/storage, DLQ depth), OpenTelemetry tracing.
5. CI/CD: verify `.github/workflows/*` actually run; GitHub OIDC deploy role in AWS (needs approval).
6. Tests: create `tests/security/`; browser-driven UI test; wire `scripts/test_postgres.sh` into CI.
7. Image: 3 HIGH CVEs in Debian base (glibc ×2, zlib) — rebuild on a patched base.
8. GitHub Pages: enable Pages, run `pages.yml` (it uses environment `github-pages-approval`).
9. Architecture diagram (last), then update gates G4/G5/G7. Gates use only PASS / FAIL / BLOCKED.

## Bring it back (≈20–25 min, starts billing ≈ $0.085/hour)

```bash
cd infra/aws-cdk
C="-c region=us-east-2 -c cloudFrontPrefixListId=pl-b6a144df -c appOrigins=https://batterymind-app.vercel.app"
PATH="$PWD/.venv/bin:$PATH" npx --yes aws-cdk@latest deploy --require-approval never --outputs-file cdk-outputs.json $C -c desiredCount=0
# then build and push the API image to the NEW repository from cdk-outputs.json (RepositoryUri):
#   docker build --platform linux/arm64 -f apps/api/Dockerfile -t batterymind-api:v7 .
#   tag and push as <RepositoryUri>:v7   (tags are immutable; always use a new tag)
PATH="$PWD/.venv/bin:$PATH" npx --yes aws-cdk@latest deploy --require-approval never --outputs-file cdk-outputs.json $C -c desiredCount=1 -c imageTag=v7
cd ../.. && ./scripts/publish_web.sh && ./scripts/publish_vercel_app.sh
.venv/bin/python -I tests/e2e/run_live.py      # creates/deletes throwaway MFA users
```

Expect on redeploy: a **new** CloudFront URL, user pool and client ID, and a new ECR repository name (the old
retained ones are orphaned; delete them only after confirming they are empty/unneeded). The publish scripts
read `cdk-outputs.json`, so the Vercel app picks up the new URLs automatically. Manisha has no Cognito user
yet; ask for the email before creating one.

## Gotchas

- Run CDK with `infra/aws-cdk/.venv` on PATH (system Python lacks `aws_cdk`).
- zsh: write `"${REPO}:v7"`, not `$REPO:v7` (`:r` is a zsh modifier).
- Bedrock: Nova Micro needs a `us.` inference profile that can leave us-east-2 — do not use it.
- `.venv` Python needs `certifi` for HTTPS (already used by `tests/e2e/run_live.py`).
- TOTP codes cannot be reused within a 30 s window (the E2E script waits).
- cdk-nag errors on disabled RDS deletion protection unless `-c allowDestroy=true` (teardown only).
- Do not commit `cdk-outputs.json`, `cdk.context.json`, `config.json`, `.vercel/`, `*.tsbuildinfo`.
- Never publish or create paid resources without Manisha's explicit approval.
