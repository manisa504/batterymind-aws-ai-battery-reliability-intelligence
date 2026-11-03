"""Generate DOC/architecture/batterymind-aws.drawio with official draw.io AWS (aws4) icons, then export SVG/PNG.

Run: python scripts/build_architecture_diagram.py   (requires the draw.io desktop CLI `drawio` on PATH)
The diagram describes the deployed system; keep it in sync with infra/aws-cdk and docs/gates.
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

cells: list[str] = []


def _add(xml: str) -> None:
    cells.append(xml)


def icon(cid, x, y, res, color, label, size=64):
    style = (
        "sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;"
        f"fillColor={color};strokeColor=#ffffff;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;"
        "align=center;html=1;fontSize=12;fontStyle=0;aspect=fixed;whiteSpace=wrap;"
        f"shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{res};"
    )
    _add(f'<mxCell id="{cid}" value="{escape(label)}" style="{style}" vertex="1" parent="1">'
         f'<mxGeometry x="{x}" y="{y}" width="{size}" height="{size}" as="geometry"/></mxCell>')


def user(cid, x, y, label):
    style = ("sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;fillColor=#232F3D;strokeColor=none;"
             "dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=12;"
             "aspect=fixed;pointerEvents=1;shape=mxgraph.aws4.user;whiteSpace=wrap;")
    _add(f'<mxCell id="{cid}" value="{escape(label)}" style="{style}" vertex="1" parent="1">'
         f'<mxGeometry x="{x}" y="{y}" width="56" height="56" as="geometry"/></mxCell>')


def external(cid, x, y, label, w=250, h=56):
    style = ("rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#545B64;fontColor=#232F3E;"
             "fontSize=12;arcSize=12;")
    _add(f'<mxCell id="{cid}" value="{label}" style="{style}" vertex="1" parent="1">'
         f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')


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
        style = ("rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#879196;dashed=1;fontColor=#545B64;"
                 "verticalAlign=top;align=left;spacingLeft=10;spacingTop=4;fontSize=13;fontStyle=1;")
    else:
        style = ("points=[];outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=13;fontStyle=1;"
                 "container=0;pointerEvents=0;collapsible=0;recursiveResize=0;shape=mxgraph.aws4.group;"
                 "verticalAlign=top;align=left;spacingLeft=30;" + styles[kind])
    _add(f'<mxCell id="{cid}" value="{escape(label)}" style="{style}" vertex="1" parent="1">'
         f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')


def edge(cid, src, dst, number, kind="live", exit_=None, entry=None, points=None):
    color = {"live": "#232F3E", "build": "#545B64", "unused": "#AAB7B8"}[kind]
    style = (f"edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeWidth={2 if kind == 'live' else 1.5};"
             f"strokeColor={color};endArrow=block;endFill=1;fontSize=11;fontStyle=1;labelBackgroundColor=#FFFFFF;"
             f"fontColor={color};")
    if kind != "live":
        style += "dashed=1;"
    if exit_:
        style += f"exitX={exit_[0]};exitY={exit_[1]};exitDx=0;exitDy=0;"
    if entry:
        style += f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;"
    pts = ""
    if points:
        pts = '<Array as="points">' + "".join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in points) + "</Array>"
    _add(f'<mxCell id="{cid}" value="{number}" style="{style}" edge="1" source="{src}" target="{dst}" parent="1">'
         f'<mxGeometry relative="1" as="geometry">{pts}</mxGeometry></mxCell>')


def text(cid, x, y, w, h, value, size=12, bold=False, align="left"):
    style = (f"text;html=1;whiteSpace=wrap;align={align};verticalAlign=top;fontSize={size};fontColor=#232F3E;"
             f"fontStyle={1 if bold else 0};spacing=4;")
    _add(f'<mxCell id="{cid}" value="{value}" style="{style}" vertex="1" parent="1">'
         f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')


# ---------------------------------------------------------------- layout
text("title", 30, 18, 900, 50,
     "<b style='font-size:20px'>BatteryMind — AWS architecture</b><br>Manisha · deployed stack BatteryMindDemo · "
     "us-east-2 · diagram v3 (2026-11-03)", size=13)

# Groups are added first so they render behind the services.
group("g_public", 30, 90, 320, 980, "Internet and third-party hosting", "plain")
group("g_cloud", 380, 90, 1390, 980, "AWS Cloud", "cloud")
group("g_region", 400, 130, 1350, 920, "Region us-east-2 (Ohio)", "region")
group("g_vpc", 640, 175, 780, 560, "VPC (no NAT gateway)", "vpc")
group("g_pub", 660, 225, 220, 480, "Public subnets", "public")
group("g_app", 905, 225, 235, 480, "Private subnets — application", "private")
group("g_db", 1165, 225, 235, 480, "Isolated subnets — database", "private")

# Internet / third party (left)
user("engineer", 162, 120, "Engineer (browser)")
external("vercel_app", 65, 240, "<b>Vercel</b> · BatteryMind app<br>React chat UI (calls AWS)")
external("vercel_showcase", 65, 360, "<b>Vercel</b> · recruiter showcase<br>static export, no AWS")
external("pages", 65, 480, "<b>GitHub Pages</b><br>DOC/index.html")
external("github", 65, 600, "<b>GitHub</b> · repository<br>+ Actions workflows")
external("ingest", 65, 740, "<b>Ingestion</b> (Python)<br>SHA-256 verified, Parquet")
external("nasa", 65, 880, "<b>NASA Ames</b><br>Li-ion battery aging data")

# Regional edge and identity services (outside VPC)
icon("cloudfront", 478, 230, "cloudfront", NETWORK, "Amazon CloudFront<br>HTTPS · web + /api/*")
icon("s3web", 478, 420, "simple_storage_service", STORAGE, "Amazon S3<br>web assets (OAC)")
icon("cognito", 478, 610, "cognito", SECURITY, "Amazon Cognito<br>MFA required")

# VPC
icon("alb", 738, 420, "elastic_load_balancing", NETWORK, "Application Load Balancer<br>CloudFront prefix list only")
icon("fargate", 990, 420, "fargate", COMPUTE, "Amazon ECS on Fargate<br>FastAPI · ARM64")
icon("rds", 1250, 420, "rds", DATABASE, "Amazon RDS PostgreSQL 16<br>pgvector · forced RLS")

# Regional services (right)
icon("bedrock", 1560, 200, "bedrock", AI, "Amazon Bedrock<br>Gemma 3 12B · Titan Embed v2")
icon("secrets", 1560, 370, "secrets_manager", SECURITY, "AWS Secrets Manager<br>database credentials")
icon("sqs", 1560, 540, "simple_queue_service", INTEGRATION, "Amazon SQS + DLQ<br>(provisioned, not yet used)")
icon("s3data", 1560, 710, "simple_storage_service", STORAGE, "Amazon S3<br>data bucket")

# Operations row
icon("ecr", 760, 850, "elastic_container_registry", COMPUTE, "Amazon ECR<br>immutable tags · scan on push")
icon("cloudwatch", 1010, 850, "cloudwatch_2", MANAGEMENT, "Amazon CloudWatch<br>logs · 30-day retention")
icon("iam", 1260, 850, "identity_and_access_management", SECURITY, "AWS IAM<br>least-privilege task role")

# ---------------------------------------------------------------- flows
edge("f1", "engineer", "vercel_app", "1")
edge("f2", "vercel_app", "cognito", "2", exit_=(1, 0.75), entry=(0, 0.5), points=[(420, 282), (420, 642)])
edge("f3", "vercel_app", "cloudfront", "3", exit_=(1, 0.25), entry=(0, 0.5))
edge("f4", "cloudfront", "s3web", "4")
edge("f5", "cloudfront", "alb", "5", exit_=(1, 0.5), entry=(0.5, 0), points=[(770, 262)])
edge("f6", "alb", "fargate", "6")
edge("f7", "fargate", "cognito", "7", exit_=(0.5, 1), entry=(1, 0.5), points=[(1022, 642)])
edge("f8", "fargate", "rds", "8")
edge("f9", "fargate", "bedrock", "9", exit_=(0.5, 0), entry=(0, 0.5), points=[(1022, 232)])
edge("f10", "fargate", "secrets", "10", exit_=(0.75, 0), entry=(0, 0.5), points=[(1038, 300), (1480, 300), (1480, 402)])
edge("f11", "fargate", "sqs", "11", kind="unused", exit_=(1, 0.75), entry=(0, 0.5),
     points=[(1150, 468), (1150, 572)])
edge("f12", "fargate", "s3data", "12", exit_=(0.75, 1), entry=(0, 0.5), points=[(1038, 742)])
edge("f13", "ecr", "fargate", "13", kind="build", exit_=(0.5, 0), entry=(0.25, 1), points=[(792, 790), (1006, 790)])
edge("f14", "fargate", "cloudwatch", "14", exit_=(0.5, 1), entry=(0.5, 0))
edge("f15", "github", "ecr", "15", kind="build", exit_=(1, 0.5), entry=(0, 0.5), points=[(380, 628), (380, 882)])
edge("f16", "github", "pages", "16", kind="build")
edge("f17", "nasa", "ingest", "17", kind="build")
edge("f18", "ingest", "vercel_showcase", "18", kind="build", exit_=(0, 0.5), entry=(0, 0.5),
     points=[(45, 768), (45, 388)])
edge("f19", "ingest", "ecr", "19", kind="build", exit_=(1, 0.75), entry=(0, 0.75), points=[(365, 782), (365, 898)])

legend = (
    "<b>Request path (solid)</b><br>"
    "1 Engineer opens the app · 2 Sign-in: Cognito hosted UI, authorization code + PKCE, authenticator-app MFA · "
    "3 API calls with the Cognito ID token (CORS limited to the app origin) · 4 Web assets for the AWS-hosted UI · "
    "5 CloudFront forwards /api/* over HTTP to an ALB that accepts only CloudFront origin addresses · "
    "6 ALB to Fargate tasks · 7 API verifies the token signature with Cognito JWKS · "
    "8 Sessions, assessments, conversation turns and embeddings, as a non-bypass role under row-level security · "
    "9 Chat (Gemma 3 12B) and embeddings (Titan Text Embeddings V2), both on-demand in us-east-2 · "
    "10 Database credentials · 12 Data bucket access · 14 Application logs<br>"
    "<b>Build and data preparation (dashed)</b><br>"
    "13 Image pull · 15 Container image build/push (workflow defined; demo images were pushed manually) · "
    "16 Documentation publish · 17 Verified NASA archive download · 18 Static JSON export for the showcase · "
    "19 Processed Parquet packaged into the API image<br>"
    "<b>Grey dashed</b>: 11 provisioned but not exercised by the application yet."
)
text("legend", 30, 1090, 1740, 130, legend, size=12)

xml = (
    '<mxfile host="drawio" version="24.7.0"><diagram id="batterymind" name="BatteryMind AWS">'
    '<mxGraphModel dx="1800" dy="1240" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" '
    'fold="1" page="1" pageScale="1" pageWidth="1800" pageHeight="1240" background="#FFFFFF" math="0" shadow="0">'
    '<root><mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(cells) + "</root></mxGraphModel></diagram></mxfile>"
)
OUT.mkdir(parents=True, exist_ok=True)
source = OUT / f"{NAME}.drawio"
source.write_text(xml)
drawio = shutil.which("drawio")
if not drawio:
    raise SystemExit(f"Wrote {source}; install the draw.io CLI to export SVG/PNG")
for fmt, extra in (("svg", []), ("png", ["-s", "2", "-b", "16"])):
    subprocess.run([drawio, "-x", "-f", fmt, *extra, "-o", str(OUT / f"{NAME}.{fmt}"), str(source)],
                   check=True, capture_output=True)
print("wrote", source, "and exports")
