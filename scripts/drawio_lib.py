# ruff: noqa: E501
"""Small helpers for generating draw.io diagrams with official AWS (aws4) icons.

Used by scripts/build_more_diagrams.py. (scripts/build_architecture_diagram.py predates this module.)
Icon shape names must match draw.io's aws4 library, e.g. s3, sqs, ecr, fargate, rds, bedrock, cognito.
"""

from __future__ import annotations

import shutil
import subprocess
from html import escape
from pathlib import Path

NETWORK, STORAGE, SECURITY, COMPUTE = "#8C4FFF", "#7AA116", "#DD344C", "#ED7100"
DATABASE, AI, INTEGRATION, MANAGEMENT = "#C925D1", "#01A88D", "#E7157B", "#E7157B"

LABEL = {
    "b": "verticalLabelPosition=bottom;verticalAlign=top;align=center;",
    "t": "verticalLabelPosition=top;verticalAlign=bottom;align=center;",
    "r": "labelPosition=right;verticalLabelPosition=middle;align=left;verticalAlign=middle;spacingLeft=6;",
}


class Diagram:
    def __init__(self, name: str, width: int, height: int):
        self.name, self.width, self.height = name, width, height
        self.cells: list[str] = []

    def _add(self, xml: str) -> None:
        self.cells.append(xml)

    def icon(self, cid, x, y, res, color, label, lab="b", size=64):
        style = (
            "sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;"
            f"fillColor={color};strokeColor=#ffffff;dashed=0;{LABEL[lab]}html=1;fontSize=12;aspect=fixed;"
            f"shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{res};"
        )
        self._add(
            f'<mxCell id="{cid}" value="{escape(label)}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{size}" height="{size}" as="geometry"/></mxCell>'
        )

    def box(self, cid, x, y, w, h, label, fill="#FFFFFF", stroke="#545B64", bold_first=True):
        style = (
            f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};fontColor=#232F3E;"
            "fontSize=12;arcSize=8;align=left;verticalAlign=top;spacing=10;"
        )
        self._add(
            f'<mxCell id="{cid}" value="{escape(label)}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )

    def group(self, cid, x, y, w, h, label):
        style = (
            "rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#879196;dashed=1;fontColor=#545B64;"
            "verticalAlign=top;align=left;spacingLeft=10;spacingTop=4;fontSize=13;fontStyle=1;"
        )
        self._add(
            f'<mxCell id="{cid}" value="{escape(label)}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )

    def text(self, cid, x, y, w, h, value, size=12):
        style = f"text;html=1;whiteSpace=wrap;align=left;verticalAlign=top;fontSize={size};fontColor=#232F3E;spacing=4;"
        self._add(
            f'<mxCell id="{cid}" value="{escape(value)}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )

    def edge(self, cid, src, dst, label="", dashed=False, exit_=None, entry=None, points=None):
        color = "#545B64" if dashed else "#232F3E"
        style = (
            f"edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeWidth={1.5 if dashed else 2};strokeColor={color};"
            f"endArrow=block;endFill=1;fontSize=11;fontStyle=1;labelBackgroundColor=#FFFFFF;fontColor={color};"
            "jumpStyle=arc;jumpSize=8;" + ("dashed=1;" if dashed else "")
        )
        if exit_:
            style += f"exitX={exit_[0]};exitY={exit_[1]};exitDx=0;exitDy=0;"
        if entry:
            style += f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;"
        pts = ""
        if points:
            pts = '<Array as="points">' + "".join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in points) + "</Array>"
        self._add(
            f'<mxCell id="{cid}" value="{escape(label)}" style="{style}" edge="1" source="{src}" target="{dst}" parent="1">'
            f'<mxGeometry relative="1" as="geometry">{pts}</mxGeometry></mxCell>'
        )

    def save(self, out_dir: Path) -> None:
        xml = (
            f'<mxfile host="drawio" version="24.7.0"><diagram id="{self.name}" name="{self.name}">'
            f'<mxGraphModel dx="{self.width}" dy="{self.height}" grid="1" gridSize="10" guides="1" tooltips="1" '
            f'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{self.width}" '
            f'pageHeight="{self.height}" background="#FFFFFF" math="0" shadow="0"><root><mxCell id="0"/>'
            '<mxCell id="1" parent="0"/>' + "".join(self.cells) + "</root></mxGraphModel></diagram></mxfile>"
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        source = out_dir / f"{self.name}.drawio"
        source.write_text(xml)
        drawio = shutil.which("drawio")
        if not drawio:
            raise SystemExit(f"Wrote {source}; install the draw.io CLI to export SVG/PNG")
        for fmt, extra in (("svg", []), ("png", ["-s", "2", "-b", "16"])):
            subprocess.run(
                [drawio, "-x", "-f", fmt, *extra, "-o", str(out_dir / f"{self.name}.{fmt}"), str(source)],
                check=True,
                capture_output=True,
            )
        print("wrote", source.name, "+ svg/png")
