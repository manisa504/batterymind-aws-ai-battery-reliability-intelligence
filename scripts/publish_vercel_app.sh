#!/usr/bin/env bash
# Deploys the BatteryMind app (apps/web) to its own Vercel project. It calls the AWS API cross-origin
# and signs in through Cognito, so it needs the AWS stack to be running. The independent recruiter
# showcase (showcase/) is a separate Vercel project and does not depend on AWS.
set -euo pipefail
cd "$(dirname "$0")/.."
project="${1:-batterymind-app}"
stage="$(mktemp -d)"
npm --prefix apps/web run build
cp -R apps/web/dist/. "$stage/"
python3 - infra/aws-cdk/cdk-outputs.json > "$stage/config.json" <<'PY'
import json, sys
o = json.load(open(sys.argv[1]))["BatteryMindDemo"]
print(json.dumps({"apiBase": o["ApiUrl"], "cognitoDomain": o["CognitoDomain"], "clientId": o["UserPoolClientId"]}))
PY
cat > "$stage/vercel.json" <<'JSON'
{"cleanUrls": true, "rewrites": [{"source": "/((?!data/|assets/|config.json).*)", "destination": "/index.html"}],
 "headers": [{"source": "/(.*)", "headers": [{"key": "X-Content-Type-Options", "value": "nosniff"},
  {"key": "Referrer-Policy", "value": "no-referrer"}, {"key": "X-Frame-Options", "value": "DENY"}]}]}
JSON
cd "$stage"
npx --yes vercel@latest link --yes --project "$project" >/dev/null
npx --yes vercel@latest deploy --prod --yes
