#!/usr/bin/env bash
# Builds apps/web, writes a runtime config.json from the CDK outputs (not committed), and syncs to S3.
set -euo pipefail
cd "$(dirname "$0")/.."
outputs=infra/aws-cdk/cdk-outputs.json
region=us-east-2
npm --prefix apps/web run build
python3 - "$outputs" > apps/web/dist/config.json <<'PY'
import json, sys
o = json.load(open(sys.argv[1]))["BatteryMindDemo"]
print(json.dumps({"apiBase": "/api/v1", "cognitoDomain": o["CognitoDomain"], "clientId": o["UserPoolClientId"]}))
PY
bucket=$(aws cloudformation describe-stack-resources --region "$region" --stack-name BatteryMindDemo \
  --query "StackResources[?ResourceType=='AWS::S3::Bucket' && contains(PhysicalResourceId,'frontend')].PhysicalResourceId" --output text)
aws s3 sync apps/web/dist "s3://${bucket}/" --region "$region" --delete
