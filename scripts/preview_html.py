#!/usr/bin/env python3
"""Render local artifact HTML only; never follows an external URL."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--width", type=int, default=1200)
    parser.add_argument("--browser", type=Path, default=Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        launch = {"headless":True}
        if args.browser.is_file():
            launch["executable_path"] = str(args.browser)
        browser = pw.chromium.launch(**launch)
        page = browser.new_page(viewport={"width":args.width,"height":1000}, device_scale_factor=1)
        page.route("http://**/*", lambda route: route.abort())
        page.route("https://**/*", lambda route: route.abort())
        results = []
        for i, source in enumerate(args.files):
            if source.suffix.lower() != ".html" or not source.is_file():
                raise ValueError("Existing local HTML files only")
            page.goto(source.resolve().as_uri())
            page.evaluate("document.fonts.ready")
            page.locator("img").evaluate_all("imgs => Promise.all(imgs.map(i => i.decode()))")
            issues = page.evaluate("""() => ({overflow: document.documentElement.scrollWidth > innerWidth,
              images: [...document.images].filter(i=>!i.complete||!i.naturalWidth).length})""")
            dest = args.out / f"{i+1:02}-{source.stem}.png"
            page.screenshot(path=str(dest), full_page=True)
            results.append({"file":str(source),"screenshot":str(dest),**issues})
        browser.close()
    (args.out / "browser-check.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results))
    return 1 if any(r["overflow"] or r["images"] for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
