"""Regenerate the evidence sections of DOC/index.html from docs/gates and reports/.

Content between <!-- generated:NAME:start --> and <!-- generated:NAME:end --> is rebuilt, so every figure
on the published page comes from a committed report. `--check` exits non-zero when the page is stale
(used in CI).

Usage: python scripts/build_docs_page.py [--check]
"""

from __future__ import annotations

import json
import re
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "DOC" / "index.html"
REPO = "https://github.com/manisa504/batterymind-aws-ai-battery-reliability-intelligence"


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text())


def gates() -> list[tuple[str, str, str, list[str]]]:
    rows = []
    for path in sorted((ROOT / "docs" / "gates").glob("G*.md")):
        lines = path.read_text().splitlines()
        gate, title = lines[0].removeprefix("# ").split(" — ", 1)
        name, status = title.rsplit(":", 1)
        bullets: list[str] = []
        for line in lines[1:]:
            if line.startswith(("- ", "* ")):
                bullets.append(line[2:].strip())
            elif bullets and line.startswith("  ") and line.strip():
                bullets[-1] += " " + line.strip()  # continuation of the previous bullet
            elif not line.strip():
                bullets.append("")  # paragraph break ends a bullet
        open_items = [b for b in bullets if re.search(r"\b(BLOCKED|FAIL)\b", b)]
        rows.append((gate, name.strip(), status.strip(), open_items))
    return rows


def code(text: str) -> str:
    """Escape text and render `backticked` spans as <code>."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", escape(text))


def evaluation_section() -> str:
    rul = load("reports/model_evaluation/rul-baselines.json")["per_cell_chronological"]
    live = load("reports/performance/live-performance.json")
    ingest = load("reports/data_quality/aws-ingestion.json")
    passed = sum(c["status"] == "PASS" for c in live["checks"])
    latency = live["latency_ms"]
    gate_rows = "".join(
        f"<tr><td>{g}</td><td>{escape(n)}</td><td><b>{escape(s)}</b></td></tr>" for g, n, s, _ in gates()
    )
    rul_rows = "".join(
        f"<tr><td>{cell}</td><td>{v['training_cutoff_cycle']}</td><td>{v['linear']['mae_ah']:.4f}</td>"
        f"<td>{v['persistence']['mae_ah']:.4f}</td></tr>"
        for cell, v in rul.items()
    )
    checks = "".join(f"<li>{escape(c['check'])}: {c['status']}</li>" for c in live["checks"])
    matches = all(ingest["matches_committed_evidence"].values())
    return f"""
        <p class="kicker">Verified results</p>
        <h2>Release claims follow executed gates.</h2>
        <p>Every figure in this section is generated from a report in the repository
        (<code>scripts/build_docs_page.py</code>). Gates use only PASS, FAIL, or BLOCKED.</p>
        <table><tr><th>Gate</th><th>Scope</th><th>Status</th></tr>{gate_rows}</table>
        <h3>RUL baselines, chronological evaluation</h3>
        <p>Mean absolute capacity error (Ah) on cycles after each cell's training cutoff; lower is better. The linear
        model beats persistence on some cells and not others, and the dataset has four cells, so no broad
        generalization is claimed.</p>
        <table><tr><th>Cell</th><th>Trained through cycle</th><th>Linear MAE</th>
        <th>Persistence MAE</th></tr>{rul_rows}</table>
        <h3>AWS ingestion run</h3>
        <p>Run <code>{escape(ingest["run_id"])}</code> on ECS Fargate downloaded and checksum-verified the NASA archive,
        rebuilt the Parquet outputs in {ingest["duration_s"]} s, and {"matched" if matches else "did not match"} the
        committed evidence byte for byte, so it {"was" if ingest["promoted_to_current"] else "was not"} promoted.</p>
        <h3>Live AWS end-to-end run</h3>
        <p>{passed} of {len(live["checks"])} checks passed on {live["executed_utc"][:10]} against the deployed stack.
        Median latency from the test client over the public URL (includes network time): chat reply
        {latency["chat"]["median"]} ms; assessment with Bedrock explanation and embedding
        {latency["assessment_with_bedrock_and_embedding"]["median"]} ms.</p>
        <details><summary>All live checks</summary><ul>{checks}</ul></details>
        <div class="actions">
          <a href="architecture/batterymind-aws.drawio">Editable diagram</a>
          <a href="architecture/batterymind-aws.md">Architecture guide</a>
          <a href="architecture/batterymind-aws.png">Architecture PNG</a>
          <a href="{REPO}/tree/main/reports">Evidence reports</a>
        </div>
      """


def limits_section() -> str:
    items = [f"<li><b>{g}</b> {code(item)}</li>" for g, _, _, open_items in gates() for item in open_items]
    open_list = f"<ul>{''.join(items)}</ul>" if items else "<p>No gate has an open BLOCKED or FAIL item.</p>"
    return f"""
        <p>The dataset is small and laboratory-specific; model performance cannot establish broad product
        generalization. RDS and the load balancer create idle cost even when ECS scales to zero, so the AWS
        stack runs on a schedule. Open items recorded in the gate files:</p>
        {open_list}
      """


def render(page: str) -> str:
    for name, builder in (("evaluation", evaluation_section), ("limits", limits_section)):
        pattern = re.compile(rf"(<!-- generated:{name}:start -->).*?(<!-- generated:{name}:end -->)", re.S)
        if not pattern.search(page):
            raise SystemExit(f"marker generated:{name} missing from {PAGE}")
        page = pattern.sub(lambda m, b=builder: m.group(1) + b() + m.group(2), page)
    return page


def main(argv: list[str]) -> int:
    current = PAGE.read_text()
    updated = render(current)
    if "--check" in argv:
        if updated != current:
            print("DOC/index.html is out of date; run python scripts/build_docs_page.py")
            return 1
        print("DOC/index.html is up to date")
        return 0
    PAGE.write_text(updated)
    print("updated", PAGE.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
