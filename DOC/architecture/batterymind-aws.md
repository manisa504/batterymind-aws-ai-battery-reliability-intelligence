# BatteryMind AWS architecture guide

The diagram separates authenticated AWS production, independent public publishing, and CI/CD.

1. Engineers load the private React application through CloudFront and authenticate through Cognito.
2. CloudFront terminates HTTPS and forwards `/api/*` to an HTTP load balancer that only accepts CloudFront origin-facing addresses; the FastAPI service on Fargate validates the Cognito ID token (JWT) on every protected request.
3. The API reads authoritative Parquet evidence from S3 and structured assessments from private RDS.
4. Bedrock receives bounded structured evidence and valid memories to produce explanations.
5. Workers consume ingestion jobs through SQS; failures move to the DLQ.
6. Secrets Manager supplies credentials and CloudWatch/OpenTelemetry captures bounded telemetry.
7. GitHub Actions uses OIDC to publish immutable ECR images and static assets.
8. Vercel receives only a versioned public JSON export; GitHub Pages receives documentation.

Key decisions: `us-east-2`; no NAT gateways; public-subnet Fargate egress with task ingress restricted to
the CloudFront-only ALB; isolated RDS; structured evidence is authoritative; public systems never access private memory.

