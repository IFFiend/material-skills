#!/usr/bin/env python3
"""Build a portable, redacted evidence-based guide from ordered local screenshots."""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps


class GuideError(ValueError):
    pass


def esc(value):
    return html.escape(str(value), quote=True)


def md_text(value):
    value = html.escape(str(value), quote=False)
    for char in "\\`*_{}[]()#+!|":
        value = value.replace(char, "\\"+char)
    return value


def box(value, width, height):
    if not isinstance(value, list) or len(value) != 4 or any(type(v) is not int for v in value):
        raise GuideError("Annotation boxes require four integer pixel coordinates")
    x, y, r, b = value
    if not (0 <= x < r <= width and 0 <= y < b <= height):
        raise GuideError("Annotation box leaves screenshot or has no area")
    return value


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise GuideError("Guide input must be a JSON object")
    for key in ("title", "audience", "prerequisites"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise GuideError(f"Missing {key}")
    if not isinstance(data.get("steps"), list) or not data["steps"]:
        raise GuideError("At least one evidenced step is required")
    if output.exists() and any(output.iterdir()):
        raise GuideError("Use an empty output directory for each revision")
    prepared, seen = [], set()
    for i, step in enumerate(data["steps"], 1):
        if not isinstance(step, dict):
            raise GuideError("Each step must be an object")
        for key in ("id", "action", "expected", "observed", "screenshot"):
            if not isinstance(step.get(key), str) or not step[key].strip():
                raise GuideError(f"Step {i} missing {key}")
        if step["id"] in seen:
            raise GuideError("Duplicate step id")
        seen.add(step["id"])
        origin = step.get("origin", "user-supplied")
        if origin not in {"user-supplied", "agent-observed", "synthetic-demo"}:
            raise GuideError("Unknown evidence origin")
        if origin == "agent-observed" and not step.get("capture_note"):
            raise GuideError("Agent-observed steps need a capture note (surface/session and observation)")
        path = Path(step["screenshot"])
        path = path if path.is_absolute() else source.parent / path
        with Image.open(path) as original:
            image = ImageOps.exif_transpose(original).convert("RGB")
        draw = ImageDraw.Draw(image)
        redactions = step.get("redact", [])
        highlights = step.get("highlight", [])
        for region in redactions:
            draw.rectangle(box(region, *image.size), fill="#172B28")
        for region in highlights:
            draw.rounded_rectangle(box(region, *image.size), radius=8, outline="#398017", width=max(3, image.width//250))
        # Redaction is irreversible in exported files; originals are never copied.
        prepared.append((step, image, origin, digest(path)))
    output.mkdir(parents=True, exist_ok=True)
    assets = output / "images"
    assets.mkdir()
    report = {"schema_version": 1, "status": "technical_pass", "behavioral_verification": "not_performed_by_builder",
              "privacy_review": "pending", "source_sha256": digest(source), "items": []}
    sections, md = [], [f"# {md_text(data['title'])}", "", md_text(data["audience"]), "", "## Before you start", "", md_text(data["prerequisites"]), ""]
    for i, (step, image, origin, source_hash) in enumerate(prepared, 1):
        filename = f"step-{i:02}.png"
        dest = assets / filename
        image.save(dest)
        item = {"step": i, "id": step["id"], "origin": origin, "capture_note": step.get("capture_note"),
                "source_sha256": source_hash, "export_sha256": digest(dest), "size": image.size,
                "redactions": len(step.get("redact", [])), "highlights": len(step.get("highlight", []))}
        report["items"].append(item)
        sections.append(f'<section><div class="step">{i:02}</div><div><h2>{esc(step["action"])}</h2><p class="expected">Expected: {esc(step["expected"])}</p><p>Observed: {esc(step["observed"])}</p><p class="evidence">Evidence: {esc(origin)} — {esc(step.get("capture_note", "Supplied screenshot; live flow not verified here"))}</p><img src="images/{filename}" alt="{esc(step["action"])}"></div></section>')
        md += [f"## {i}. {md_text(step['action'])}", "", f"Expected: {md_text(step['expected'])}", "", f"Observed: {md_text(step['observed'])}", "", f"Evidence: {origin}", "", f"![Step {i}](images/{filename})", ""]
    css = 'body{margin:0;background:#f2f0e9;color:#172b28;font:17px/1.6 system-ui}main{max-width:1000px;margin:auto;padding:64px 32px}header{border-bottom:2px solid;padding-bottom:35px}h1{font-size:48px;line-height:1.1;max-width:800px}h2{font-size:25px;margin:0 0 12px}.eyebrow,.evidence{font:12px/1.5 monospace;color:#53675e}section{display:grid;grid-template-columns:50px 1fr;gap:18px;padding:40px 0;border-bottom:1px solid #bfc7bc}.step{font-size:25px;font-weight:700}img{max-width:100%;height:auto;margin-top:18px;border:1px solid #bfc7bc;border-radius:8px}.expected{font-weight:600}@media print{section{break-inside:avoid}main{padding:0}h1{font-size:32px}}'
    document = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{esc(data["title"])}</title><style>{css}</style></head><body><main><header><p class="eyebrow">FIELD GUIDE / EVIDENCE FIRST</p><h1>{esc(data["title"])}</h1><p>{esc(data["audience"])}</p><p><strong>Before you start:</strong> {esc(data["prerequisites"])}</p><p class="evidence">Technical export complete. Privacy and behavioral review remain separate.</p></header>{"".join(sections)}</main></body></html>'
    (output / "index.html").write_text(document, encoding="utf-8")
    (output / "guide.md").write_text("\n".join(md), encoding="utf-8")
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = build(args.input, args.out)
        print(json.dumps({"status": result["status"], "steps": len(result["items"]), "behavioral_verification": result["behavioral_verification"]}))
        return 0
    except (GuideError, OSError, ValueError, TypeError) as exc:
        print(f"guide: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
