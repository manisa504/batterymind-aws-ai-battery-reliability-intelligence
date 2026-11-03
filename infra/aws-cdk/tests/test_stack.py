import aws_cdk as cdk
from aws_cdk.assertions import Match, Template
from stacks.batterymind_stack import BatteryMindStack


def template():
    app = cdk.App(
        context={
            "certificateArn": "arn:aws:acm:us-east-2:111111111111:certificate/00000000-0000-0000-0000-000000000000"
        }
    )
    stack = BatteryMindStack(app, "Test", env=cdk.Environment(account="111111111111", region="us-east-2"))
    return Template.from_stack(stack)


def test_no_nat_gateway_and_database_is_private():
    result = template()
    result.resource_count_is("AWS::EC2::NatGateway", 0)
    result.has_resource_properties(
        "AWS::RDS::DBInstance", {"PubliclyAccessible": False, "StorageEncrypted": True, "DeletionProtection": True}
    )


def test_authentication_and_encryption_controls_exist():
    result = template()
    result.has_resource_properties("AWS::Cognito::UserPool", {"MfaConfiguration": "ON"})
    result.has_resource_properties("AWS::ElasticLoadBalancingV2::Listener", {"Port": 80, "Protocol": "HTTP"})
    result.has_resource_properties(
        "AWS::EC2::SecurityGroupIngress", {"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80, "SourcePrefixListId": "pl-b6a144df"}
    )
    result.resource_properties_count_is(
        "AWS::EC2::SecurityGroupIngress", {"CidrIp": "0.0.0.0/0", "FromPort": 80}, 0
    )
    result.has_resource_properties(
        "AWS::S3::Bucket", {"PublicAccessBlockConfiguration": Match.object_like({"BlockPublicAcls": True})}
    )


def test_initial_deployment_stays_scaled_to_zero_and_pins_bedrock_models():
    result = template()
    result.has_resource_properties("AWS::ECS::Service", {"DesiredCount": 0})
    result.has_resource_properties(
        "AWS::ECS::TaskDefinition",
        {
            "ContainerDefinitions": Match.array_with(
                [
                    Match.object_like(
                        {
                            "Environment": Match.array_with(
                                [
                                    {"Name": "BATTERYMIND_BEDROCK_MODEL_ID", "Value": "amazon.nova-micro-v1:0"},
                                    {
                                        "Name": "BATTERYMIND_BEDROCK_EMBEDDING_MODEL_ID",
                                        "Value": "amazon.titan-embed-text-v2:0",
                                    },
                                ]
                            )
                        }
                    )
                ]
            )
        },
    )
