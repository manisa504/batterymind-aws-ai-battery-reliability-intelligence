# BatteryMind handoff — 2026-11-06

## Free public portfolio

- Repository: https://github.com/manisa504/batterymind-aws-ai-battery-reliability-intelligence
- Documentation: https://manisa504.github.io/batterymind-aws-ai-battery-reliability-intelligence/
- Recruiter showcase: https://batterymind-showcase.vercel.app
- Vercel application: https://batterymind-app.vercel.app — deployed in **offline mode** (no `config.json`): the data views
  work and the Assistant, history and evaluation views show an offline notice. After redeploying AWS, run
  `scripts/publish_vercel_app.sh` (live mode) to reconnect it.
- Overview video: `DOC/assets/batterymind-brag.mp4` (also on the Pages site); rebuild with `scripts/build_brag_video.py`.
- No paid custom domain is configured.

## AWS status

The `BatteryMindDemo` release was deployed and fully validated in us-east-2 on image `v14`, then intentionally
destroyed on 2026-11-06 to eliminate ongoing AWS charges. Post-teardown checks found no BatteryMind CloudFormation
stack, S3 bucket, ECR repository, Cognito pool, RDS instance or snapshot, ECS cluster, load balancer, or log group.
The former AWS/CloudFront URL is offline by design.

Historical evidence remains committed:

- Real NASA ingestion and deterministic Parquet hashes: `reports/data_quality/aws-ingestion.json`
- Live MFA, Bedrock, pgvector, isolation, concurrency and restart suite: `reports/performance/live-performance.json`
- OpenTelemetry/X-Ray traces: `reports/performance/otel-traces.json`
- Deployment and teardown inventory: `reports/release/aws-deployment.json`

## Reprovisioning

Deployment and teardown procedures are in `docs/runbooks/deployment.md`. Paid AWS provisioning requires Manisha's
separate authorization. Use us-east-2 and do not use cross-region `us.` Bedrock inference profiles.

GitHub Actions OIDC creation remains blocked by an AWS Organizations SCP. Manual deployment from a reviewed CDK
diff was verified. Do not commit credentials, raw data, private memories, caches, CDK outputs, or Vercel state.

## Release artifacts (2026-11-06)

- Four draw.io diagrams with official AWS icons in `DOC/architecture/` (AWS, memory, data, delivery); regenerate with
  `scripts/build_architecture_diagram.py` and `scripts/build_more_diagrams.py` (needs the draw.io CLI).
- README documents the whole project and embeds all four diagrams; the explainer page has the video and diagrams.
- Fixed unformatted chart axes in the showcase and app; both redeployed to Vercel.
- Remaining blocker: G7 — GitHub Actions OIDC deploy role denied by an AWS Organizations policy.
