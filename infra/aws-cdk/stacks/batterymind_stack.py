from __future__ import annotations

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import (
    aws_cloudfront as cloudfront,
)
from aws_cdk import (
    aws_cloudfront_origins as origins,
)
from aws_cdk import (
    aws_cognito as cognito,
)
from aws_cdk import (
    aws_ec2 as ec2,
)
from aws_cdk import (
    aws_ecr as ecr,
)
from aws_cdk import (
    aws_ecs as ecs,
)
from aws_cdk import (
    aws_elasticloadbalancingv2 as elbv2,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_logs as logs,
)
from aws_cdk import (
    aws_rds as rds,
)
from aws_cdk import (
    aws_s3 as s3,
)
from aws_cdk import (
    aws_secretsmanager as secretsmanager,
)
from aws_cdk import (
    aws_sqs as sqs,
)
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct


class BatteryMindStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self._validate_region()

        access_logs = s3.Bucket(
            self,
            "AccessLogs",
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            object_ownership=s3.ObjectOwnership.OBJECT_WRITER,
            lifecycle_rules=[s3.LifecycleRule(expiration=Duration.days(90))],
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        NagSuppressions.add_resource_suppressions(
            access_logs,
            [
                NagPackSuppression(
                    id="AwsSolutions-S1",
                    reason="This is the terminal access-log bucket; recursive logging is not useful.",
                )
            ],
        )
        data_bucket = self._bucket("Data", retain=True, access_logs=access_logs)
        frontend_bucket = self._bucket("Frontend", retain=False, access_logs=access_logs)
        distribution = cloudfront.Distribution(
            self,
            "FrontendDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(frontend_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
            ),
            default_root_object="index.html",
            minimum_protocol_version=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
            enable_logging=True,
            log_bucket=access_logs,
            log_file_prefix="cloudfront/",
        )
        NagSuppressions.add_resource_suppressions(
            distribution,
            [
                NagPackSuppression(
                    id="AwsSolutions-CFR4",
                    reason=(
                        "The default CloudFront certificate is used with the explicitly configured "
                        "TLSv1.2_2021 minimum policy."
                    ),
                ),
                NagPackSuppression(
                    id="AwsSolutions-CFR5",
                    reason=(
                        "The no-custom-domain demo terminates TLS 1.2+ at CloudFront. Its HTTP ALB origin "
                        "accepts port 80 only from the AWS-managed CloudFront origin-facing prefix list."
                    ),
                ),
            ],
        )

        vpc = ec2.Vpc(
            self,
            "Vpc",
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(name="public-compute", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24),
                ec2.SubnetConfiguration(name="private-data", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, cidr_mask=24),
            ],
        )
        vpc.add_flow_log("FlowLog")
        db_security_group = ec2.SecurityGroup(self, "DatabaseSecurityGroup", vpc=vpc, allow_all_outbound=False)
        api_security_group = ec2.SecurityGroup(self, "ApiSecurityGroup", vpc=vpc, allow_all_outbound=True)
        db_security_group.add_ingress_rule(api_security_group, ec2.Port.tcp(5432), "PostgreSQL from API tasks")

        database_secret = secretsmanager.Secret(
            self,
            "DatabaseSecret",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username":"batterymind"}',
                generate_string_key="password",
                exclude_punctuation=True,
            ),
        )
        database = rds.DatabaseInstance(
            self,
            "Database",
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.of("16.15", "16")),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.MICRO),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[db_security_group],
            credentials=rds.Credentials.from_secret(database_secret),
            database_name="batterymind",
            allocated_storage=20,
            max_allocated_storage=100,
            storage_encrypted=True,
            multi_az=False,
            backup_retention=Duration.days(1),
            deletion_protection=True,
            removal_policy=RemovalPolicy.SNAPSHOT,
            publicly_accessible=False,
            cloudwatch_logs_exports=["postgresql"],
        )
        NagSuppressions.add_resource_suppressions(
            database,
            [
                NagPackSuppression(
                    id="AwsSolutions-RDS3",
                    reason=(
                        "Single-AZ is an explicit scheduled-demo cost tradeoff; production promotion requires Multi-AZ."
                    ),
                ),
                NagPackSuppression(
                    id="AwsSolutions-RDS11",
                    reason="PostgreSQL stays on 5432 and is reachable only from the API security group.",
                ),
            ],
        )
        NagSuppressions.add_resource_suppressions(
            database_secret,
            [
                NagPackSuppression(
                    id="AwsSolutions-SMG4",
                    reason=(
                        "The scheduled-demo database is torn down and regenerated; live production "
                        "promotion must add automatic rotation."
                    ),
                )
            ],
        )

        dead_letter_queue = sqs.Queue(
            self,
            "IngestionDeadLetterQueue",
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            enforce_ssl=True,
            retention_period=Duration.days(14),
        )
        ingestion_queue = sqs.Queue(
            self,
            "IngestionQueue",
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            enforce_ssl=True,
            visibility_timeout=Duration.minutes(15),
            dead_letter_queue=sqs.DeadLetterQueue(queue=dead_letter_queue, max_receive_count=3),
        )
        repository = ecr.Repository(
            self,
            "ApiRepository",
            image_scan_on_push=True,
            image_tag_mutability=ecr.TagMutability.IMMUTABLE,
            encryption=ecr.RepositoryEncryption.AES_256,
            lifecycle_rules=[ecr.LifecycleRule(max_image_count=10)],
            removal_policy=RemovalPolicy.RETAIN,
        )
        cluster = ecs.Cluster(self, "Cluster", vpc=vpc, container_insights_v2=ecs.ContainerInsights.ENABLED)
        log_group = logs.LogGroup(
            self, "ApiLogs", retention=logs.RetentionDays.ONE_MONTH, removal_policy=RemovalPolicy.DESTROY
        )
        task = ecs.FargateTaskDefinition(
            self,
            "ApiTask",
            cpu=512,
            memory_limit_mib=1024,
            runtime_platform=ecs.RuntimePlatform(cpu_architecture=ecs.CpuArchitecture.ARM64),
        )
        container = task.add_container(
            "Api",
            image=ecs.ContainerImage.from_ecr_repository(repository, "release"),
            logging=ecs.LogDrivers.aws_logs(stream_prefix="api", log_group=log_group),
            environment={
                "BATTERYMIND_AWS_REGION": self.region,
                "BATTERYMIND_BEDROCK_MODEL_ID": "amazon.nova-micro-v1:0",
                "BATTERYMIND_BEDROCK_EMBEDDING_MODEL_ID": "amazon.titan-embed-text-v2:0",
                "BATTERYMIND_DATABASE_HOST": database.db_instance_endpoint_address,
                "BATTERYMIND_DATABASE_PORT": database.db_instance_endpoint_port,
                "BATTERYMIND_DATABASE_NAME": "batterymind",
                "BATTERYMIND_DATA_BUCKET": data_bucket.bucket_name,
                "BATTERYMIND_ALLOWED_ORIGIN": "https://batterymind-showcase.vercel.app",
                "BATTERYMIND_LOCAL_AUTH_ENABLED": "false",
            },
            secrets={
                "BATTERYMIND_DATABASE_USER": ecs.Secret.from_secrets_manager(database_secret, "username"),
                "BATTERYMIND_DATABASE_PASSWORD": ecs.Secret.from_secrets_manager(database_secret, "password"),
            },
            health_check=ecs.HealthCheck(
                command=[
                    "CMD-SHELL",
                    "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\"",
                ]
            ),
        )
        container.add_port_mappings(ecs.PortMapping(container_port=8000))
        data_bucket.grant_read_write(task.task_role)
        database_secret.grant_read(task.task_role)
        task.task_role.add_to_principal_policy(
            iam.PolicyStatement(
                actions=["bedrock:Converse", "bedrock:InvokeModel"],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/amazon.nova-micro-v1:0",
                    f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v2:0",
                ],
            )
        )
        NagSuppressions.add_resource_suppressions(
            task.task_role,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason=(
                        "The task needs object-prefix access in its dedicated data bucket and model "
                        "access is constrained to Bedrock model resource types."
                    ),
                )
            ],
            apply_to_children=True,
        )
        if task.execution_role is not None:
            NagSuppressions.add_resource_suppressions(
                task.execution_role,
                [
                    NagPackSuppression(
                        id="AwsSolutions-IAM5",
                        reason=(
                            "ECS-generated ECR pull and CloudWatch log-stream permissions require "
                            "service resource wildcards."
                        ),
                    )
                ],
                apply_to_children=True,
            )
        NagSuppressions.add_resource_suppressions(
            task,
            [
                NagPackSuppression(
                    id="AwsSolutions-ECS2",
                    reason=(
                        "Only non-secret deployment configuration is passed as environment variables; "
                        "credentials use ECS secrets."
                    ),
                )
            ],
        )

        service = ecs.FargateService(
            self,
            "ApiService",
            cluster=cluster,
            task_definition=task,
            # The first deployment creates the immutable ECR repository. After the
            # release image is pushed, deploy again with -c desiredCount=1.
            desired_count=int(self.node.try_get_context("desiredCount") or 0),
            assign_public_ip=True,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_groups=[api_security_group],
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            min_healthy_percent=100,
        )
        load_balancer_security_group = ec2.SecurityGroup(
            self, "LoadBalancerSecurityGroup", vpc=vpc, allow_all_outbound=False
        )
        cloudfront_prefix_list = self.node.try_get_context("cloudFrontPrefixListId") or "pl-b6a144df"
        load_balancer_security_group.add_ingress_rule(
            ec2.Peer.prefix_list(cloudfront_prefix_list), ec2.Port.tcp(80), "CloudFront origin traffic only"
        )
        api_security_group.add_ingress_rule(load_balancer_security_group, ec2.Port.tcp(8000), "Only load balancer")
        load_balancer = elbv2.ApplicationLoadBalancer(
            self, "LoadBalancer", vpc=vpc, internet_facing=True, security_group=load_balancer_security_group
        )
        load_balancer.log_access_logs(access_logs, "alb")
        NagSuppressions.add_resource_suppressions(
            load_balancer_security_group,
            [
                NagPackSuppression(
                    id="AwsSolutions-EC23",
                    reason="The internet-facing entry point intentionally allows only TCP 443 from IPv4 clients.",
                )
            ],
        )
        container.add_environment("BATTERYMIND_ALB_ARN", load_balancer.load_balancer_arn)
        target_group = elbv2.ApplicationTargetGroup(
            self,
            "ApiTargets",
            vpc=vpc,
            port=8000,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(path="/health"),
        )
        service.attach_to_application_target_group(target_group)

        user_pool = cognito.UserPool(
            self,
            "UserPool",
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(email=True),
            mfa=cognito.Mfa.REQUIRED,
            feature_plan=cognito.FeaturePlan.PLUS,
            mfa_second_factor=cognito.MfaSecondFactor(sms=False, otp=True),
            password_policy=cognito.PasswordPolicy(
                min_length=14, require_digits=True, require_lowercase=True, require_uppercase=True, require_symbols=True
            ),
            removal_policy=RemovalPolicy.RETAIN,
        )
        domain = user_pool.add_domain(
            "Domain", cognito_domain=cognito.CognitoDomainOptions(domain_prefix=f"batterymind-{self.account}")
        )
        user_pool_client = user_pool.add_client(
            "AlbClient",
            generate_secret=False,
            auth_flows=cognito.AuthFlow(user_password=True),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[cognito.OAuthScope.OPENID, cognito.OAuthScope.EMAIL],
                callback_urls=[f"https://{distribution.distribution_domain_name}/"],
            ),
            prevent_user_existence_errors=True,
        )
        listener = load_balancer.add_listener("Http", port=80, open=False)
        listener.add_target_groups("Forward", target_groups=[target_group])
        distribution.add_behavior(
            "api/*",
            origins.LoadBalancerV2Origin(
                load_balancer,
                protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
                http_port=80,
            ),
            allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
            cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
            cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
            origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
            viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
        )
        container.add_environment("BATTERYMIND_COGNITO_USER_POOL_ID", user_pool.user_pool_id)
        container.add_environment("BATTERYMIND_COGNITO_CLIENT_ID", user_pool_client.user_pool_client_id)
        ingestion_queue.grant_consume_messages(task.task_role)

        CfnOutput(self, "FrontendUrl", value=f"https://{distribution.distribution_domain_name}")
        CfnOutput(self, "ApiUrl", value=f"https://{distribution.distribution_domain_name}/api/v1")
        CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id)
        CfnOutput(self, "CognitoDomain", value=domain.base_url())
        CfnOutput(self, "RepositoryUri", value=repository.repository_uri)

    def _bucket(self, name: str, *, retain: bool, access_logs: s3.IBucket) -> s3.Bucket:
        return s3.Bucket(
            self,
            name,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            lifecycle_rules=[s3.LifecycleRule(noncurrent_version_expiration=Duration.days(30))],
            server_access_logs_bucket=access_logs,
            server_access_logs_prefix=f"s3/{name.lower()}/",
            removal_policy=RemovalPolicy.RETAIN if retain else RemovalPolicy.DESTROY,
            auto_delete_objects=not retain,
        )

    def _validate_region(self) -> None:
        if self.region != "us-east-2":
            raise ValueError("BatteryMind defaults to us-east-2; change only with explicit project authorization")
