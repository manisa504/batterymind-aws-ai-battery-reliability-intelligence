# ruff: noqa: E501
"""Generate DOC/architecture/batterymind-aws.drawio with official draw.io AWS (aws4) icons, then export SVG/PNG.

Run: python scripts/build_architecture_diagram.py   (requires the draw.io desktop CLI `drawio` on PATH)
The diagram describes the system defined in infra/aws-cdk; keep it in sync with the stack and docs/gates.
"""

from __future__ import annotations

import shutil
import subprocess
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "DOC" / "architecture"
NAME = "batterymind-aws"

# AWS Architecture Icons category colours.
NETWORK, STORAGE, SECURITY, COMPUTE = "#8C4FFF", "#7AA116", "#DD344C", "#ED7100"
DATABASE, AI, INTEGRATION, MANAGEMENT = "#C925D1", "#01A88D", "#E7157B", "#E7157B"

LABEL = {
    "b": "verticalLabelPosition=bottom;verticalAlign=top;align=center;",
    "t": "verticalLabelPosition=top;verticalAlign=bottom;align=center;",
    "r": "labelPosition=right;verticalLabelPosition=middle;align=left;verticalAlign=middle;spacingLeft=6;",
}

cells: list[str] = []


def _add(xml: str) -> None:
    cells.append(xml)


def icon(cid, x, y, res, color, label, lab="b", size=64):
    style = (
        "sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;"
        f"fillColor={color};strokeColor=#ffffff;dashed=0;{LABEL[lab]}html=1;fontSize=12;fontStyle=0;aspect=fixed;"
        f"shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{res};"
    )
    _add(
        f'<mxCell id="{cid}" value="{escape(label)}" style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{size}" height="{size}" as="geometry"/></mxCell>'
    )


def user(cid, x, y, label):
    style = (
        "sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;fillColor=#232F3D;strokeColor=none;"
        f"dashed=0;{LABEL['r']}html=1;fontSize=12;aspect=fixed;pointerEvents=1;shape=mxgraph.aws4.user;"
    )
    _add(
        f'<mxCell id="{cid}" value="{escape(label)}" style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="56" height="56" as="geometry"/></mxCell>'
    )


def external(cid, x, y, label, w=250, h=56):
    style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#545B64;fontColor=#232F3E;fontSize=12;arcSize=12;"
    _add(
        f'<mxCell id="{cid}" value="{escape(label)}" style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )


def group(cid, x, y, w, h, label, kind):
    styles = {
        "cloud": "grIcon=mxgraph.aws4.group_aws_cloud_alt;strokeColor=#232F3E;fillColor=none;fontColor=#232F3E;dashed=0;",
        "region": "grIcon=mxgraph.aws4.group_region;strokeColor=#00A4A6;fillColor=none;fontColor=#147EBA;dashed=1;",
        "vpc": "grIcon=mxgraph.aws4.group_vpc2;strokeColor=#8C4FFF;fillColor=none;fontColor=#8C4FFF;dashed=0;",
        "public": "grIcon=mxgraph.aws4.group_security_group;grStroke=0;strokeColor=#7AA116;fillColor=#F2F6E8;"
        "fontColor=#248814;dashed=0;",
        "private": "grIcon=mxgraph.aws4.group_security_group;grStroke=0;strokeColor=#00A4A6;fillColor=#E6F6F7;"
        "fontColor=#147EBA;dashed=0;",
    }
    if kind == "plain":
        style = (
            "rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#879196;dashed=1;fontColor=#545B64;"
            "verticalAlign=top;align=left;spacingLeft=10;spacingTop=4;fontSize=13;fontStyle=1;"
        )
    else:
        style = (
            "points=[];outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=13;fontStyle=1;"
            "container=0;pointerEvents=0;collapsible=0;recursiveResize=0;shape=mxgraph.aws4.group;"
            "verticalAlign=top;align=left;spacingLeft=30;" + styles[kind]
        )
    _add(
        f'<mxCell id="{cid}" value="{escape(label)}" style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )


def edge(cid, src, dst, number, kind="live", exit_=None, entry=None, points=None):
    color = {"live": "#232F3E", "build": "#545B64"}[kind]
    style = (
        f"edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeWidth={2 if kind == 'live' else 1.5};"
        f"strokeColor={color};endArrow=block;endFill=1;fontSize=11;fontStyle=1;labelBackgroundColor=#FFFFFF;"
        f"fontColor={color};jumpStyle=arc;jumpSize=8;"
    )
    if kind != "live":
        style += "dashed=1;"
    if exit_:
        style += f"exitX={exit_[0]};exitY={exit_[1]};exitDx=0;exitDy=0;"
    if entry:
        style += f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;"
    pts = ""
    if points:
        pts = '<Array as="points">' + "".join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in points) + "</Array>"
    _add(
        f'<mxCell id="{cid}" value="{number}" style="{style}" edge="1" source="{src}" target="{dst}" parent="1">'
        f'<mxGeometry relative="1" as="geometry">{pts}</mxGeometry></mxCell>'
    )


def text(cid, x, y, w, h, value, size=12, bold=False):
    style = f"text;html=1;whiteSpace=wrap;align=left;verticalAlign=top;fontSize={size};fontColor=#232F3E;fontStyle={1 if bold else 0};spacing=4;"
    _add(
        f'<mxCell id="{cid}" value="{escape(value)}" style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )


# ------------------------------------------------------------------ groups (drawn first, rendered behind)
text(
    "title",
    30,
    14,
    1500,
    56,
    "<b style='font-size:22px'>BatteryMind — AWS architecture</b><br>Manisha · region us-east-2 · validated on image v14, "
    "stack torn down 2026-11-06 to remove charges · reproducible from infra/aws-cdk · diagram v4",
    size=13,
)
group("g_ext", 30, 90, 320, 1030, "Internet, hosting and data sources", "plain")
group("g_cloud", 380, 90, 1520, 1040, "AWS Cloud", "cloud")
group("g_region", 400, 130, 1480, 980, "Region us-east-2 (Ohio)", "region")
group("g_vpc", 700, 165, 700, 660, "VPC — no NAT gateway", "vpc")
group("g_pub", 720, 225, 455, 350, "Public subnets", "public")
group("g_db", 1195, 225, 185, 350, "Isolated subnets", "private")
group("g_right", 1930, 90, 250, 1040, "Operator", "plain")

# ------------------------------------------------------------------ left: users, hosting, sources
user("engineer", 160, 118, "Engineer (browser)")
external("vercel_app", 60, 334, "<b>Vercel</b> · BatteryMind app<br>React chat UI, calls the AWS API")
external("vercel_showcase", 60, 454, "<b>Vercel</b> · recruiter showcase<br>static export, no AWS")
external("pages", 60, 574, "<b>GitHub Pages</b><br>explainer (DOC/index.html)")
external("github", 60, 694, "<b>GitHub</b> · repository<br>CI workflows")
external("nasa", 60, 834, "<b>NASA Ames</b><br>Li-ion battery aging data")

# ------------------------------------------------------------------ region edge services
icon("cloudfront", 500, 330, "cloudfront", NETWORK, "Amazon CloudFront<br>HTTPS · web + /api/*", "t")
icon("s3web", 500, 470, "s3", STORAGE, "Amazon S3<br>web assets", "r")
icon("cognito", 500, 640, "cognito", SECURITY, "Amazon Cognito<br>MFA required", "r")

# ------------------------------------------------------------------ VPC
icon("alb", 770, 330, "application_load_balancer", NETWORK, "Application Load Balancer<br>CloudFront origin only", "t")
icon("api", 1000, 330, "fargate", COMPUTE, "ECS Fargate · API<br>FastAPI + CloudWatch agent sidecar", "b")
icon("ingest", 770, 470, "fargate", COMPUTE, "ECS Fargate · ingestion task<br>batch, ARM64", "t")
icon("rds", 1255, 330, "rds", DATABASE, "RDS PostgreSQL 16<br>pgvector · forced RLS", "b")

# ------------------------------------------------------------------ right column
icon("bedrock", 1640, 190, "bedrock", AI, "Amazon Bedrock<br>Gemma 3 12B · Titan Embed v2", "r")
icon("secrets", 1640, 330, "secrets_manager", SECURITY, "AWS Secrets Manager<br>database credentials", "r")
icon("pipe", 1500, 470, "eventbridge_pipes", INTEGRATION, "EventBridge Pipe", "t")
icon("sqs", 1640, 470, "sqs", INTEGRATION, "Amazon SQS + DLQ<br>ingestion requests", "t")
icon("s3data", 1640, 610, "s3", STORAGE, "Amazon S3 · data<br>raw archive, Parquet", "r")
icon("xray", 1640, 750, "xray", MANAGEMENT, "AWS X-Ray<br>traces (OpenTelemetry)", "r")
icon("cloudwatch", 1640, 890, "cloudwatch", MANAGEMENT, "Amazon CloudWatch<br>logs, Container Insights, 5 alarms", "r")

# ------------------------------------------------------------------ operations row
icon("ecr", 1000, 950, "ecr", COMPUTE, "Amazon ECR<br>immutable tags, scan on push", "b")
icon("iam", 1240, 950, "identity_and_access_management", SECURITY, "AWS IAM<br>least-privilege task roles", "b")
external("operator", 1950, 474, "<b>Operator</b><br>sends a versioned ingestion request", w=210)

# ------------------------------------------------------------------ flows
edge("f1", "engineer", "vercel_app", "1", exit_=(0.5, 1), entry=(0.5, 0))
edge("f2", "vercel_app", "cognito", "2", exit_=(1, 0.8), entry=(0, 0.5), points=[(440, 379), (440, 672)])
edge("f3", "vercel_app", "cloudfront", "3", exit_=(1, 0.5), entry=(0, 0.5))
edge("f4", "cloudfront", "s3web", "4", exit_=(0.5, 1), entry=(0.5, 0))
edge("f5", "cloudfront", "alb", "5", exit_=(1, 0.5), entry=(0, 0.5))
edge("f6", "alb", "api", "6", exit_=(1, 0.5), entry=(0, 0.5))
edge("f7", "api", "cognito", "7", exit_=(0.25, 0), entry=(0, 0.5), points=[(1016, 190), (460, 190), (460, 672)])
edge("f8", "api", "rds", "8", exit_=(1, 0.5), entry=(0, 0.5))
# Fan-out from the API to regional services. Farthest target gets the smallest x and the lowest run, so the
# routes nest without crossing each other.
for cid, dst, num, ty, run_y, turn_x in (
    ("f9", "bedrock", "9", 222, 190, 1485),
    ("f10", "secrets", "10", 362, 197, 1470),
    ("f15", "s3data", "15", 642, 204, 1455),
    ("f16", "xray", "16", 782, 211, 1440),
    ("f17", "cloudwatch", "17", 922, 218, 1425),
):
    edge(cid, "api", dst, num, exit_=(0.75, 0), entry=(0, 0.5), points=[(1048, run_y), (turn_x, run_y), (turn_x, ty)])
edge("f11", "operator", "sqs", "11", kind="build", exit_=(0, 0.5), entry=(1, 0.5))
edge("f12", "sqs", "pipe", "12", exit_=(0, 0.5), entry=(1, 0.5))
edge("f13", "pipe", "ingest", "13", exit_=(0, 0.5), entry=(1, 0.5))
edge("f14", "ingest", "s3data", "14", exit_=(0.5, 1), entry=(0, 0.5), points=[(802, 642)])
edge("f18", "nasa", "ingest", "18", kind="build", exit_=(1, 0.5), entry=(0.75, 1), points=[(818, 862)])
edge("f19", "ecr", "g_pub", "19", kind="build", exit_=(0.5, 0), entry=(0.69, 1))
edge("f20", "github", "ecr", "20", kind="build", exit_=(1, 0.5), entry=(0, 0.5), points=[(420, 722), (420, 982)])
edge("f21", "github", "pages", "21", kind="build", exit_=(0.5, 0), entry=(0.5, 1))

legend = (
    "<b>Request and data flows (solid)</b><br>"
    "1 Engineer opens the Vercel app · 2 Sign-in through the Cognito hosted UI (authorization code + PKCE, "
    "authenticator-app MFA) · 3 The app calls the API with the Cognito ID token (CORS limited to the app origin) · "
    "4 AWS-hosted web assets · 5 CloudFront forwards /api/* over HTTP to a load balancer that accepts only CloudFront "
    "origin addresses · 6 Load balancer to the Fargate API · 7 The API verifies tokens against Cognito's signing keys · "
    "8 Sessions, assessments, conversation turns and embeddings in PostgreSQL/pgvector, queried as a non-bypass role under "
    "row-level security · 9 Chat (Gemma 3 12B) and embeddings (Titan Text Embeddings V2), both on-demand in us-east-2 · "
    "10 Database credentials · 12–13 SQS to an EventBridge Pipe that starts the ingestion task · 14 The task verifies the NASA "
    "archive hash, stores the raw archive and Parquet outputs, and promotes them only if they match committed evidence · "
    "15 The API reads promoted data · 16 OpenTelemetry spans via a CloudWatch agent sidecar · 17 Logs, metrics and alarms<br>"
    "<b>Operator, build and publishing flows (dashed)</b><br>"
    "11 Operator request · 18 NASA archive download · 19 Image pull · 20 Image build and push (the deploy workflow exists, but "
    "an AWS Organizations policy blocks the OIDC role, so images were pushed manually) · 21 Documentation publish. "
    "The API and ingestion tasks run in public subnets with public IPs because the design avoids a NAT gateway; security groups "
    "admit only the load balancer."
)
text("legend", 30, 1150, 2150, 150, legend, size=12)

xml = (
    '<mxfile host="drawio" version="24.7.0"><diagram id="batterymind" name="BatteryMind AWS">'
    '<mxGraphModel dx="2200" dy="1300" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" '
    'fold="1" page="1" pageScale="1" pageWidth="2200" pageHeight="1320" background="#FFFFFF" math="0" shadow="0">'
    '<root><mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(cells) + "</root></mxGraphModel></diagram></mxfile>"
)
OUT.mkdir(parents=True, exist_ok=True)
source = OUT / f"{NAME}.drawio"
source.write_text(xml)
drawio = shutil.which("drawio")
if not drawio:
    raise SystemExit(f"Wrote {source}; install the draw.io CLI to export SVG/PNG")
for fmt, extra in (("svg", []), ("png", ["-s", "2", "-b", "16"])):
    subprocess.run(
        [drawio, "-x", "-f", fmt, *extra, "-o", str(OUT / f"{NAME}.{fmt}"), str(source)],
        check=True,
        capture_output=True,
    )
print("wrote", source, "and exports")
