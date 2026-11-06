#!/usr/bin/env bash
# Deploys the BatteryMind app (apps/web) to its own Vercel project.
#   scripts/publish_vercel_app.sh [project]             live mode: config.json from infra/aws-cdk/cdk-outputs.json
#   scripts/publish_vercel_app.sh [project] --offline   no config.json: the app shows an offline notice
# Live mode calls the AWS API cross-origin and signs in through Cognito, so the AWS stack must be running.
# The independent recruiter showcase (showcase/) is a separate Vercel project and never depends on AWS.
set -euo pipefail
cd "$(dirname "$0")/.."
project="${1:-batterymind-app}"
stage="$(mktemp -d)"
npm --prefix apps/web run build
cp -R apps/web/dist/. "$stage/"
if [ "${2:-}" != "--offline" ]; then
python3 - infra/aws-cdk/cdk-outputs.json > "$stage/config.json" <<'PY'
import json, sys
o = json.load(open(sys.argv[1]))["BatteryMindDemo"]
print(json.dumps({"apiBase": o["ApiUrl"], "cognitoDomain": o["CognitoDomain"], "clientId": o["UserPoolClientId"]}))
PY
fi
cat > "$stage/vercel.json" <<'JSON'
{"cleanUrls": true, "rewrites": [{"source": "/((?!data/|assets/|config.json).*)", "destination": "/index.html"}],
 "headers": [{"source": "/(.*)", "headers": [{"key": "X-Content-Type-Options", "value": "nosniff"},
  {"key": "Referrer-Policy", "value": "no-referrer"}, {"key": "X-Frame-Options", "value": "DENY"}]}]}
JSON
cd "$stage"
npx --yes vercel@latest link --yes --project "$project" >/dev/null
npx --yes vercel@latest deploy --prod --yes
