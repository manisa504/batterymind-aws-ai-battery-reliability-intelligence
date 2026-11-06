# BatteryMind handoff — 2026-11-06

Read this, then `AGENTS.md` and `docs/gates/`. Gates use only PASS / FAIL / BLOCKED.

## Live release

- AWS `BatteryMindDemo` is live in us-east-2 at https://d2e0z15r8r846m.cloudfront.net using immutable ARM64
  image `v14` (`sha256:6c275dfd304583f61803f9983dafbd02e01674a7152bd44f0a5c094415da1ba8`).
- ECS is steady at 1/1. RDS PostgreSQL/pgvector is private; Cognito MFA, Bedrock, SQS ingestion, CloudWatch alarms
  and X-Ray tracing were verified live.
- Vercel app: https://batterymind-app.vercel.app
- Vercel showcase: https://batterymind-showcase.vercel.app
- GitHub Pages: https://manisa504.github.io/batterymind-aws-ai-battery-reliability-intelligence/
- Repository: https://github.com/manisa504/batterymind-aws-ai-battery-reliability-intelligence

## Acceptance evidence

- Real NASA ingestion run `aws-20261106-v14`: PASS; 2,167 cycles, 2,089,050 samples and 42,576 impedance rows;
  deterministic Parquet hashes match committed evidence (`reports/data_quality/aws-ingestion.json`).
- Live end-to-end suite on `v14`: PASS, including two-user MFA, Bedrock explanations, Titan embeddings, pgvector
  memory, cross-user isolation, idempotent concurrent writes, corrections, deletion and ECS restart persistence
  (`reports/performance/live-performance.json`).
- OpenTelemetry to X-Ray: PASS, four current release traces (`reports/performance/otel-traces.json`).
- ECR scan: COMPLETE. Five HIGH findings are in upstream Debian base packages (glibc x2, zlib x2, apt); AWS ECR
  reports no fixed versions. Rebuild when upstream fixes are published.

## External blocker

- GitHub Actions OIDC: BLOCKED by an explicit AWS Organizations SCP denial. Account administration must allow the
  OIDC provider before CI can deploy directly. Manual releases use reviewed `cdk diff` output.

## Operations

- Region is always `us-east-2`. Do not use `us.` Bedrock inference profiles because they can route out of region.
- CDK outputs are local in `infra/aws-cdk/cdk-outputs.json` and intentionally ignored by Git.
- Teardown and redeploy procedures are in `docs/runbooks/` and `README.md`; RDS/storage costs remain until
  teardown, even if ECS is scaled to zero.
- Do not commit raw NASA data, credentials, generated caches, private memories, CDK outputs or Vercel state.
