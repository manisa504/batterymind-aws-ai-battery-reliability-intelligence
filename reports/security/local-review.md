# Local security review

- CDK assertions confirm no NAT gateway, private encrypted RDS with deletion protection, HTTPS ALB,
  Cognito MFA configuration, and private S3 controls.
- The API verifies the ALB-signed OIDC JWT signer, ES256 signature, expiry, and subject. The development
  identity header works only when local auth is explicitly enabled.
- PostgreSQL policies force per-user row-level security; the repository sets the transaction-local user.
- ECR tags are immutable and scanned, task ingress is limited to the ALB security group, credentials use
  Secrets Manager, and Bedrock output/retries are bounded.
- Both npm dependency audits reported zero known vulnerabilities at high severity or above.
- `cdk-nag` reports zero errors. Two advisory warnings remain: geographic restrictions and AWS WAF are
  not enabled for this cost-controlled demonstration distribution.

Open items: live AWS IAM/SCP evaluation, Cognito browser flow, ALB public-key verification, secret
rotation, CloudTrail review, and container-image scanning require the authorized AWS account.

