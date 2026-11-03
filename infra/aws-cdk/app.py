#!/usr/bin/env python3
import os

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks
from stacks.batterymind_stack import BatteryMindStack

app = cdk.App(outdir="cdk.out")
region = app.node.try_get_context("region") or "us-east-2"
account = os.environ.get("CDK_DEFAULT_ACCOUNT", "111111111111")
stack = BatteryMindStack(app, "BatteryMindDemo", env=cdk.Environment(account=account, region=region))
cdk.Aspects.of(stack).add(AwsSolutionsChecks(verbose=True))
app.synth()
