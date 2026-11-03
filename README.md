# BatteryMind

BatteryMind is Manisha's AWS-native battery reliability intelligence portfolio project. It
turns authentic NASA Ames battery aging experiments into traceable measurements, transparent
analytics, versioned engineering classifications, and persistent assessment memory.

The project distinguishes measured values, derived metrics, predictions, and LLM explanations.
It does not present laboratory observations as field safety outcomes.

## Current evidence

- The candidate NASA archive is reachable and contains B0005, B0006, B0007, and B0018.
- The downloaded archive SHA-256 is recorded in `data/manifests/nasa-source.json`.
- Local builds and tests are recorded under `docs/gates/` after execution.
- The AWS stack (CDK: ECS Fargate ARM64, RDS PostgreSQL + pgvector, Cognito with MFA, CloudFront, SQS,
  ECR) was deployed and tested live in `us-east-2`: authenticated assessment memory in RDS and
  Amazon Bedrock (Nova Micro) explanations, which only rephrase values already computed by the rules.
  Embedding-based recall and the SQS path are not yet exercised; gate G5 is PARTIAL
  (`reports/release/aws-deployment.json`).

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
make install
make ingest
make test
npm --prefix apps/web install && npm --prefix apps/web run build
npm --prefix showcase install && npm --prefix showcase run build
```

Raw archives and processed Parquet files are deliberately ignored by Git. The ingestion command
reproduces the committed manifests, schema documentation, reports, and public showcase export.

See [DOC/index.html](DOC/index.html), [the PRD](docs/PRD.md), and
[deployment runbook](docs/runbooks/deployment.md).

Public recruiter showcase: https://batterymind-showcase.vercel.app

