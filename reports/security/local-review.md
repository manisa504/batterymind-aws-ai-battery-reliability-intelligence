# Security review

Reviewed 2026-11-06 against the current code and CDK stack. Each item names the executed evidence.

## Verified by tests

- **Authentication** (`tests/security/test_auth.py`): forged, expired, wrong-audience, wrong-issuer, `alg=none`,
  HS256-confusion, access-token and missing-subject tokens are rejected; every memory route requires a token; the
  impersonation header is ignored unless local auth is enabled, and local auth cannot be enabled outside
  `environment=local`.
- **Input and CORS**: invalid query strings, battery ids and over-long chat messages are rejected before any work;
  unknown origins get no CORS header.
- **Tenant isolation**: PostgreSQL row-level security is forced and applied through a non-bypass role for every
  transaction (`tests/memory/test_postgres.py`); live cross-user checks all passed
  (`reports/performance/live-performance.json`).
- **Infrastructure** (`infra/aws-cdk/tests/test_security.py`): no NAT gateway; RDS private and encrypted; database
  credentials come from Secrets Manager, not environment variables; every S3 bucket blocks public access, encrypts and
  requires TLS; no security group is open to the internet; Bedrock access is limited to two `us-east-2` model ARNs;
  no administrative IAM wildcards; Cognito requires MFA, strong passwords and admin-created users only; the tracing
  sidecar is pinned and listens on localhost only.

## Verified by tooling

- `cdk-nag` reports **zero errors**. Two advisory warnings remain (CloudFront geographic restriction and AWS WAF),
  intentionally not enabled for a cost-controlled demonstration.
- `npm audit --audit-level=high` reports zero vulnerabilities for `apps/web` and `showcase`.

## Known gaps

- The container image scan reports three HIGH findings in Debian base packages (glibc ×2, zlib) with no upstream fix.
- The CloudFront-to-ALB hop is HTTP, restricted by security group to CloudFront's origin-facing address list;
  viewer traffic is HTTPS (TLS 1.2+). A custom domain and certificate would allow HTTPS end to end.
- The API and ingestion tasks run in public subnets with public IPs (no NAT gateway); security groups admit only the load balancer.
- Secret rotation, CloudTrail review and WAF rules were not exercised.
- GitHub Actions cannot assume an AWS role (an AWS Organizations policy denies creating the OIDC provider).
