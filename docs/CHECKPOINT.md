# BatteryMind handoff — 2026-11-03

## Live release

- AWS `BatteryMindDemo`, `us-east-2`: https://dve60f8xmf6go.cloudfront.net
- Real app on free Vercel hostname: https://batterymind-app.vercel.app
- Independent recruiter showcase: https://batterymind-showcase.vercel.app
- AWS API and ingestion use immutable ARM64 image `v12`.
- Promoted data source: `s3://batteryminddemo-data666c94c7-zuz86wz32zeq/processed/current/cycles.parquet`.

## Completed evidence

- AWS NASA ingestion: PASS — `reports/data_quality/aws-ingestion.json`.
- Live AWS API/Cognito/RDS/Bedrock/memory suite: PASS — `reports/performance/live-performance.json`.
- Cross-session recall, correction/supersession, concurrent idempotent writes, forced-container restart,
  deletion, wrong-user isolation, and historical cutoffs: PASS.
- Analysis voltage/temperature profiles, measured-vs-predicted trajectory, cutoff-derived RUL uncertainty: built.
- Evaluation operating-cost inventory: built and served live.
- CloudWatch alarms: API 5xx/task count, RDS CPU/storage, and DLQ depth deployed.
- Browser-driven recruiter interactions: PASS — `tests/browser/showcase.mjs`.
- Vercel production aliases refreshed; no paid custom domain.

## Explicit blockers

- OpenTelemetry trace export: BLOCKED. The required first-time ADOT onboarding skill
  `setting-up-cloudwatch-observability` is unavailable; do not invent a collector setup.
- GitHub Actions OIDC role: BLOCKED. AWS Organizations SCP explicitly denies IAM OIDC provider inspection
  and creation for the authenticated account role. Manual reviewed CDK deployment remains operational.

These blockers do not invalidate data, analytics, memory, application, ingestion, or browser evidence, but
they prevent G5/G7 from being represented as fully complete.
