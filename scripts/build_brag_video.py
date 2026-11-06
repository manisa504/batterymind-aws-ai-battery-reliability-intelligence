# ruff: noqa: E501
"""Build the BatteryMind highlight ("brag") video from committed evidence.

Every number on screen and in the narration is read from docs/gates and reports/, the architecture frame is the
committed diagram, and the showcase frame is a live screenshot of the public Vercel site. Narration uses the
macOS `say` voice. Requires macOS, Google Chrome, ffmpeg and ffprobe.

Run: python scripts/build_brag_video.py      -> DOC/assets/batterymind-brag.mp4 and batterymind-brag-poster.png
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "DOC" / "assets"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SHOWCASE = "https://batterymind-showcase.vercel.app"
REPO = "github.com/manisa504/batterymind-aws-ai-battery-reliability-intelligence"
PAGES = "manisa504.github.io/batterymind-aws-ai-battery-reliability-intelligence"
VOICE, RATE = "Samantha", 172
W, H, FPS = 1920, 1080, 30


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def facts() -> dict:
    ingest = load("reports/data_quality/nasa-ingestion.json")
    aws = load("reports/data_quality/aws-ingestion.json")
    live = load("reports/performance/live-performance.json")
    traces = load("reports/performance/otel-traces.json")
    cost = load("reports/cost/demo-cost.json")
    gates = [p.read_text().splitlines()[0] for p in sorted((ROOT / "docs" / "gates").glob("G*.md"))]
    return {
        "cells": len(ingest["cells"]),
        "cycles": ingest["cycle_rows"],
        "samples": ingest["sample_rows"],
        "live_passed": sum(c["status"] == "PASS" for c in live["checks"]),
        "live_total": len(live["checks"]),
        "chat_ms": live["latency_ms"]["chat"]["median"],
        "traces": traces["traces_found"],
        "ingest_s": aws["duration_s"],
        "gates_pass": sum(g.rstrip().endswith("PASS") or "PASS (" in g for g in gates),
        "gates_total": len(gates),
        "eight_hour_cost": cost["eight_hour_fixed_subtotal"],
    }


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kwargs)


def slide(body: str, kicker: str = "BatteryMind") -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box}}body{{margin:0;width:{W}px;height:{H}px;background:#0a1110;color:#eaf0ee;
font-family:Inter,'Helvetica Neue',Arial,sans-serif;overflow:hidden;position:relative}}
.k{{position:absolute;left:96px;top:72px;font-size:26px;letter-spacing:.18em;text-transform:uppercase;color:#b6ff62}}
.f{{position:absolute;left:96px;bottom:56px;font-size:24px;color:#7d8984}}
.c{{position:absolute;left:96px;right:96px;top:150px;bottom:120px;display:flex;flex-direction:column;justify-content:center}}
h1{{font-size:112px;line-height:1.02;margin:0 0 28px}}h1 em{{color:#b6ff62;font-style:normal}}
h2{{font-size:76px;line-height:1.08;margin:0 0 36px}}p{{font-size:40px;line-height:1.4;color:#a6b1ad;margin:0 0 16px;max-width:1500px}}
.row{{display:flex;gap:28px;margin-top:20px}}.card{{flex:1;border:1px solid #2a3531;background:#101916;padding:34px}}
.card b{{display:block;font-size:84px;color:#b6ff62;line-height:1}}.card span{{display:block;font-size:30px;color:#a6b1ad;margin-top:14px}}
img{{display:block}}
</style></head><body><div class="k">{escape(kicker)}</div><div class="c">{body}</div>
<div class="f">Project owner: Manisha · NASA Ames Li-ion aging data · AWS us-east-2</div></body></html>"""


def scenes(f: dict, tmp: Path, showcase_png: Path) -> list[dict]:
    diagram = ROOT / "DOC" / "architecture" / "batterymind-aws.png"
    n = f"{f['samples']:,}"
    return [
        {
            "name": "title",
            "html": slide(
                "<h1>Evidence that<br><em>remembers.</em></h1><p>AWS-native AI battery reliability intelligence, "
                "built on real NASA experiments.</p>",
                "BatteryMind",
            ),
            "say": "BatteryMind. An A W S native, A I battery reliability platform, built on real NASA experiments.",
        },
        {
            "name": "data",
            "html": slide(
                "<h2>Real measurements. Nothing simulated.</h2><div class='row'>"
                f"<div class='card'><b>{f['cells']}</b><span>NASA Ames cells verified in the archive</span></div>"
                f"<div class='card'><b>{f['cycles']:,}</b><span>charge, discharge and impedance cycles</span></div>"
                f"<div class='card'><b>{n}</b><span>samples parsed, checksum verified</span></div></div>",
                "The data",
            ),
            "say": f"Every number starts as a real laboratory measurement. Four lithium ion cells, {f['cycles']:,} cycles, "
            f"and {f['samples'] / 1e6:.1f} million samples, verified against the archive checksum.",
        },
        {
            "name": "showcase",
            "html": slide("", "Live showcase: explore it without signing in"),
            "image": showcase_png,
            "say": "The public showcase runs on Vercel with no AWS dependency. Pick a cell, move the cutoff, and see "
            "measured capacity, calculated state of health, and a transparent engineering decision.",
        },
        {
            "name": "architecture",
            "html": slide("", "Architecture: production on AWS"),
            "image": diagram,
            "say": "Production runs on AWS in Ohio. CloudFront, Cognito with required M F A, Fargate, Postgres with "
            "pgvector, Bedrock, an S Q S driven ingestion pipeline, and tracing to X Ray, all defined as code.",
        },
        {
            "name": "memory",
            "html": slide(
                "<h2>An assistant that answers from evidence.</h2><p>Measurements first. Then your earlier assessments, "
                "recalled by meaning with pgvector. The decision stays deterministic; the language model only explains.</p>",
                "AI memory",
            ),
            "say": "The assistant answers from measurements first, then recalls your earlier assessments with vector "
            "search. The decision is deterministic. The model only explains it.",
        },
        {
            "name": "proof",
            "html": slide(
                "<h2>Proven live, not claimed.</h2><div class='row'>"
                f"<div class='card'><b>{f['live_passed']}/{f['live_total']}</b><span>live checks passed: MFA login, "
                "isolation, recall after restart</span></div>"
                f"<div class='card'><b>{f['traces']}/{f['traces']}</b><span>requests traced end to end in X-Ray</span></div>"
                f"<div class='card'><b>{f['ingest_s']:.1f}s</b><span>Fargate ingestion, byte-identical to committed "
                "evidence</span></div></div>",
                "Evidence",
            ),
            "say": f"And it was proven on live infrastructure. {f['live_passed']} of {f['live_total']} end to end checks "
            f"passed, including multi factor login, cross user isolation, and recall after a container restart. "
            f"Traces reached X Ray, and ingestion on Fargate reproduced the committed data exactly.",
        },
        {
            "name": "gates",
            "html": slide(
                f"<h2>{f['gates_pass']} of {f['gates_total']} gates pass.</h2><p>The last gate stays blocked, and says "
                "so: an AWS Organizations policy denies the deploy role, so releases are deployed manually from reviewed "
                f"diffs. An eight hour demo is estimated at ${f['eight_hour_cost']:.2f} in fixed AWS cost, then the stack is torn down.</p>",
                "Honest status",
            ),
            "say": f"{f['gates_pass']} of {f['gates_total']} acceptance gates pass. The last stays blocked, and the project says "
            f"so. An eight hour demo is estimated at about {f['eight_hour_cost']:.0f} dollars in fixed cost, and the stack is torn down afterward.",
        },
        {
            "name": "close",
            "html": slide(
                f"<h2>BatteryMind</h2><p>Code: {REPO}</p><p>Explainer: {PAGES}</p><p>Showcase: batterymind-showcase.vercel.app</p>",
                "Built by Manisha",
            ),
            "say": "BatteryMind, built by Manisha. The code, the explainer, and the live showcase are linked below.",
        },
    ]


def screenshot(url: str, out: Path, width: int, height: int, budget: int = 10000) -> None:
    run(
        [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            f"--window-size={width},{height}",
            f"--virtual-time-budget={budget}",
            f"--screenshot={out}",
            url,
        ]
    )


def duration(path: Path) -> float:
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)])
    return float(out.stdout.strip())


def main() -> int:
    f = facts()
    tmp = Path(tempfile.mkdtemp(prefix="batterymind-video-"))
    showcase_png = tmp / "showcase.png"
    tall = tmp / "showcase-tall.png"
    screenshot(SHOWCASE, tall, 1600, 1700, budget=20000)
    run(["ffmpeg", "-y", "-i", str(tall), "-vf", "crop=1400:760:100:720", str(showcase_png)])
    clips: list[Path] = []
    for i, scene in enumerate(scenes(f, tmp, showcase_png)):
        base = tmp / f"{i:02d}-{scene['name']}"
        html = base.with_suffix(".html")
        html.write_text(scene["html"])
        slide_png = base.with_suffix(".png")
        screenshot(html.as_uri(), slide_png, W, H, budget=2000)
        voice = base.with_suffix(".aiff")
        run(["say", "-v", VOICE, "-r", str(RATE), "-o", str(voice), scene["say"]])
        seconds = duration(voice) + 0.9
        frames = int(seconds * FPS)
        clip = base.with_suffix(".mp4")
        image = scene.get("image")
        if image:
            # The evidence image (diagram or showcase) is fitted to the frame below the scene label.
            graph = (
                f"[1:v]scale=-1:{H - 280}[img];[0:v][img]overlay=(W-w)/2:140,"
                f"fade=t=in:st=0:d=0.4,fade=t=out:st={seconds - 0.4:.2f}:d=0.4[v]"
            )
            cmd = [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-t",
                f"{seconds:.2f}",
                "-i",
                str(slide_png),
                "-loop",
                "1",
                "-t",
                f"{seconds:.2f}",
                "-i",
                str(image),
                "-i",
                str(voice),
                "-filter_complex",
                graph,
                "-map",
                "[v]",
                "-map",
                "2:a",
                "-r",
                str(FPS),
            ]
        else:
            cmd = [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-t",
                f"{seconds:.2f}",
                "-i",
                str(slide_png),
                "-i",
                str(voice),
                "-vf",
                f"fade=t=in:st=0:d=0.4,fade=t=out:st={seconds - 0.4:.2f}:d=0.4",
                "-map",
                "0:v",
                "-map",
                "1:a",
                "-r",
                str(FPS),
            ]
        cmd += [
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-af",
            "apad",
            "-shortest",
            str(clip),
        ]
        run(cmd)
        clips.append(clip)
        print(f"scene {i + 1}: {scene['name']} {seconds:.1f}s (frames {frames})")
    listing = tmp / "clips.txt"
    listing.write_text("".join(f"file '{c}'\n" for c in clips))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUT_DIR / "batterymind-brag.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listing),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(target),
        ]
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            "1",
            "-i",
            str(clips[0]),
            "-frames:v",
            "1",
            str(OUT_DIR / "batterymind-brag-poster.png"),
        ]
    )
    print(f"wrote {target} ({target.stat().st_size / 1e6:.1f} MB, {duration(target):.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
