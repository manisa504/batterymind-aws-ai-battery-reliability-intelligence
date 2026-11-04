"""Infrastructure security assertions on the synthesized template (spec §14)."""

import json

from test_stack import template


def resources(result, kind):
    return {k: v for k, v in result.to_json()["Resources"].items() if v["Type"] == kind}


def test_every_bucket_blocks_public_access_encrypts_and_requires_tls():
    result = template()
    buckets = resources(result, "AWS::S3::Bucket")
    assert buckets
    for name, bucket in buckets.items():
        props = bucket["Properties"]
        block = props["PublicAccessBlockConfiguration"]
        assert all(block[k] for k in ("BlockPublicAcls", "BlockPublicPolicy", "IgnorePublicAcls", "RestrictPublicBuckets")), name
        assert props.get("BucketEncryption"), name
    policies = json.dumps(resources(result, "AWS::S3::BucketPolicy"))
    assert policies.count('"aws:SecureTransport": "false"') >= len(buckets)


def test_no_security_group_allows_the_internet_except_none():
    result = template()
    for kind in ("AWS::EC2::SecurityGroup", "AWS::EC2::SecurityGroupIngress"):
        for name, sg in resources(result, kind).items():
            rules = sg["Properties"].get("SecurityGroupIngress", [sg["Properties"]])
            for rule in rules:
                assert rule.get("CidrIp") != "0.0.0.0/0", name
                assert rule.get("CidrIpv6") != "::/0", name


def test_database_is_private_encrypted_and_credentials_come_from_secrets_manager():
    result = template()
    (db,) = resources(result, "AWS::RDS::DBInstance").values()
    assert db["Properties"]["PubliclyAccessible"] is False
    assert db["Properties"]["StorageEncrypted"] is True
    for task in resources(result, "AWS::ECS::TaskDefinition").values():
        for container in task["Properties"]["ContainerDefinitions"]:
            names = {e["Name"] for e in container.get("Environment", [])}
            assert not any("PASSWORD" in n or "SECRET" in n for n in names), names
    api = next(
        c for t in resources(result, "AWS::ECS::TaskDefinition").values()
        for c in t["Properties"]["ContainerDefinitions"] if any(e["Name"] == "BATTERYMIND_LOCAL_AUTH_ENABLED"
                                                                for e in c.get("Environment", []))
    )
    env = {e["Name"]: e["Value"] for e in api["Environment"] if isinstance(e["Value"], str)}
    assert env["BATTERYMIND_LOCAL_AUTH_ENABLED"] == "false"
    assert env["BATTERYMIND_ENVIRONMENT"] == "production"
    assert {s["Name"] for s in api["Secrets"]} >= {"BATTERYMIND_DATABASE_USER", "BATTERYMIND_DATABASE_PASSWORD"}


def test_bedrock_permissions_are_limited_to_two_models_in_us_east_2():
    result = template()
    statements = [
        s for p in resources(result, "AWS::IAM::Policy").values()
        for s in p["Properties"]["PolicyDocument"]["Statement"]
        if any(str(a).startswith("bedrock:") for a in (s["Action"] if isinstance(s["Action"], list) else [s["Action"]]))
    ]
    assert statements
    arns = [json.dumps(r) for s in statements for r in (s["Resource"] if isinstance(s["Resource"], list) else [s["Resource"]])]
    assert arns and all("us-east-2" in a and "foundation-model/" in a for a in arns), arns
    assert not any(a == '"*"' for a in arns)


def test_no_iam_policy_grants_admin_wildcards():
    result = template()
    for name, policy in resources(result, "AWS::IAM::Policy").items():
        for statement in policy["Properties"]["PolicyDocument"]["Statement"]:
            actions = statement["Action"] if isinstance(statement["Action"], list) else [statement["Action"]]
            assert "*" not in actions, name
            assert not any(a.endswith(":*") and a.split(":")[0] in ("iam", "rds", "ec2", "s3") for a in actions), (
                name, actions)


def test_cognito_requires_mfa_strong_passwords_and_no_self_sign_up():
    result = template()
    (pool,) = resources(result, "AWS::Cognito::UserPool").values()
    props = pool["Properties"]
    assert props["MfaConfiguration"] == "ON"
    assert props["Policies"]["PasswordPolicy"]["MinimumLength"] >= 14
    assert props["AdminCreateUserConfig"]["AllowAdminCreateUserOnly"] is True
