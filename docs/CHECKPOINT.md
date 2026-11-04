# BatteryMind handoff — 2026-11-04

Read this, then `AGENTS.md` and `docs/gates/`. Gates use only PASS / FAIL / BLOCKED.

## State at stop

- **AWS stack `BatteryMindDemo` (us-east-2) was spun down on 2026-11-04 at Manisha's request.** Retained by design
  (≈ $0.07/day): RDS final snapshot, S3 data bucket (raw + processed NASA data), ECR repositories, Cognito user pools
  (0 users). Two orphaned resources from the first teardown also remain and can be deleted once confirmed unneeded:
  ECR repository `batteryminddemo-apirepositoryb8378b43-q3gpazlzplzy` and user pool `UserPool6BA7E5F2-q9coRe1PoUDK`.
- **Vercel**: showcase https://batterymind-showcase.vercel.app (static, no AWS) stays live. The app
  https://batterymind-app.vercel.app is deployed but needs AWS running to work.
- **GitHub**: https://github.com/manisa504/batterymind-aws-ai-battery-reliability-intelligence — CI green from
  commit `ab727d2` onward.
- **GitHub Pages**: page content is current and generated (`scripts/build_docs_page.py`), but Pages is not enabled.

## Verified (evidence in `reports/`)

- Real NASA data; analytics, SOH, RUL with uncertainty, deterministic policy; analysis profiles and cost views.
- AWS ingestion SQS → EventBridge Pipe → ECS → S3, byte-identical promotion (`reports/data_quality/aws-ingestion.json`).
- Live E2E 24/24 on image `v12` incl. cross-session recall, correction, concurrency, restart
  (`reports/performance/live-performance.json`).
- OpenTelemetry → CloudWatch agent sidecar → X-Ray: 4/4 live requests traced on `v13`
  (`reports/performance/otel-traces.json`).
- CloudWatch alarms (API 5xx, task count, RDS CPU/storage, DLQ depth).
- Security: `tests/security/` and `infra/aws-cdk/tests/test_security.py`; local header auth is fail-closed and
  refused outside `environment=local`; production sets `BATTERYMIND_ENVIRONMENT=production`.
- CI: real archive download + SHA-256, ingestion/export reproducibility, docs-page sync, lint, unit, security,
  PostgreSQL, CDK, browser tests.

## Open items (in order)

1. Re-run `tests/e2e/run_live.py` on image `v13` after redeploying (G5).
2. Enable GitHub Pages and publish `DOC/` (G7). `pages.yml` uses environment `github-pages-approval`;
   `actions/deploy-pages` may require the environment to be named `github-pages`.
3. Architecture diagram **last** (Manisha's instruction): `scripts/build_architecture_diagram.py` with official
   aws4 icons. Facts to reflect: API and ingestion tasks run in **public** subnets with public IPs (no NAT); RDS in
   isolated subnets; CloudFront → ALB (CloudFront prefix list only); CloudWatch agent sidecar → X-Ray; SQS →
   EventBridge Pipe → ECS ingestion task; Vercel app calls the API with CORS.
4. GitHub Actions OIDC deploy role: BLOCKED by an AWS Organizations SCP — needs the account administrator.
5. Image: 3 HIGH CVEs in Debian base packages (glibc ×2, zlib), no fixed versions published yet.
6. Manisha has no Cognito user; ask for her email before creating one.

## Bring it back (≈ 25 min; billing resumes ≈ $0.085/hour)

```bash
cd infra/aws-cdk
C="-c region=us-east-2 -c cloudFrontPrefixListId=pl-b6a144df -c appOrigins=https://batterymind-app.vercel.app"
PATH="$PWD/.venv/bin:$PATH" npx --yes aws-cdk@latest deploy --require-approval never --outputs-file cdk-outputs.json $C -c desiredCount=0
# Build and push the API image to RepositoryUri from cdk-outputs.json with a NEW tag (tags are immutable), e.g. v14:
#   docker build --platform linux/arm64 -f apps/api/Dockerfile -t batterymind-api:v14 .
PATH="$PWD/.venv/bin:$PATH" npx --yes aws-cdk@latest deploy --require-approval never --outputs-file cdk-outputs.json $C -c desiredCount=1 -c imageTag=v14
cd ../.. && ./scripts/publish_web.sh && ./scripts/publish_vercel_app.sh
# Re-run ingestion (sends the SQS message) and the live suite:
.venv/bin/python -I tests/e2e/run_live.py
```

A redeploy creates a new CloudFront URL, user pool and client ID; the publish scripts read `cdk-outputs.json`.

## Spin down

```bash
cd infra/aws-cdk
C="... same context as the last deploy ... -c allowDestroy=true"
PATH="$PWD/.venv/bin:$PATH" npx --yes aws-cdk@latest deploy --require-approval never $C   # lifts RDS deletion protection
PATH="$PWD/.venv/bin:$PATH" npx --yes aws-cdk@latest destroy --force $C
```

## Gotchas

- Use `infra/aws-cdk/.venv` for CDK; zsh needs `"${URI}:v14"` (`:r` is a zsh modifier).
- Run commit gates with `set -o pipefail`; piping pytest into `tail` hides failures.
- Do not use Bedrock `us.` inference profiles (they can leave us-east-2).
- Do not commit `cdk-outputs.json`, `cdk.context.json`, `config.json`, `.vercel/`, `*.tsbuildinfo`, raw data.
- Never publish or create paid resources without Manisha's explicit approval.
