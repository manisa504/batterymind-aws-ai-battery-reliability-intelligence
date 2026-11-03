# AWS demonstration cost assumptions

Price evidence retrieved 2026-11-02 from AWS public Price List files for `us-east-2` and official AWS
pricing pages. Prices exclude tax and can change; refresh immediately before deployment.

| Resource | Verified unit price | 8-hour demo window | 720-hour always-on reference |
|---|---:|---:|---:|
| RDS PostgreSQL db.t4g.micro | $0.016/hour | $0.13 | $11.52 |
| RDS gp2, 20 GB | $0.115/GB-month | $2.30/month | $2.30/month |
| ECS Fargate ARM, 0.5 vCPU + 1 GB | $0.03238/vCPU-hour + $0.00356/GB-hour | $0.16 | $14.22 |
| Application Load Balancer | $0.0225/hour | $0.18 | $16.20 |
| ALB capacity, assumed ≤1 LCU | $0.008/LCU-hour | ≤$0.06 | ≤$5.76 |
| Public IPv4, assumed 3 addresses | $0.005/address-hour | $0.12 | $10.80 |

The modeled 8-hour fixed-resource subtotal is about **$2.95**, dominated by a full month of retained
20 GB database storage. The always-on reference is about **$60.80/month** before S3, CloudFront, ECR,
database snapshots, logs, data transfer, Bedrock tokens/embeddings, and taxes. Actual ALB address count,
LCUs, and usage must be verified from the deployed account.

Cost controls: scheduled deployment/teardown, 20 GB initial RDS storage, one small ARM Fargate task,
no NAT gateways, 30-day logs, ECR image retention, S3 noncurrent-version expiration, Bedrock output cap,
and separate approval before provisioning. RDS retained snapshots and buckets continue to incur storage
cost after stack teardown.

Sources:

- https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/us-east-2/index.json
- https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonECS/current/us-east-2/index.json
- https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSELB/current/us-east-2/index.json
- https://aws.amazon.com/vpc/pricing/

