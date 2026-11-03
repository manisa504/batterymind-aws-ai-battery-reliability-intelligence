# Deployment and teardown runbook

No deployment is authorized by this document. Before provisioning, verify the AWS identity belongs
to Manisha's project, confirm the AWS Projects home Region, list Bedrock models in `us-east-2`,
review the synthesized template and `cdk diff`, and approve the current price estimate.

The scheduled-demo topology has unavoidable idle cost from RDS, the load balancer, public IPv4
addresses, and retained storage. Scaling ECS to zero does not remove those charges.

1. Supply a valid `us-east-2` ACM certificate ARN and deploy with standard `cdk deploy`. The default
   `desiredCount=0` creates the repository without starting a task that references a missing image.
2. Build the ARM64 API image, push the immutable `release` tag to the stack's ECR repository, then
   review the new diff and deploy with `-c desiredCount=1`.
3. Apply the pgvector schema, ingest the verified export, and execute live integration tests.
4. Record stack outputs and test evidence without credentials or private data.
5. Scale ECS to zero between demonstrations with a reviewed `-c desiredCount=0` deployment.
6. For teardown, export required evidence, disable deletion protection by reviewed CDK change, run
   `cdk diff`, deploy that change, then destroy. Retained data buckets, database snapshot, ECR images,
   and Cognito user pool require a separately reviewed cleanup step.

Production must never use CDK hotswap or express mode.

