#!/usr/bin/env python3
"""Local, measured event graphics. No model/API calls or silent copy edits."""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import io
import json
import math
import re
import sys
from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont, ImageOps
from fontTools.ttLib import TTFont

SIZES = {"square": (1080, 1080), "portrait": (1080, 1350), "wide": (1920, 1080)}
FAMILIES = {"editorial", "signal", "ticket"}


class InputError(ValueError):
    pass


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def font_path(value, base):
    if value:
        p = Path(value).expanduser()
        if not p.is_absolute():
            p = base / p
        if not p.is_file():
            raise InputError(f"Font not found: {p}")
        return p.resolve()
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return Path(candidate)
    raise InputError("Supply brand.font_regular and brand.font_bold; no supported system font found")


def color(value):
    if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        raise InputError(f"Expected six-digit hex colour, got {value!r}")
    return value


def contrast(a, b):
    def lum(c):
        rgb = [int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        rgb = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
        return sum(v * k for v, k in zip(rgb, (.2126, .7152, .0722)))
    x, y = sorted((lum(a), lum(b)))
    return (y + .05) / (x + .05)


def resolve_asset(value, base):
    p = Path(value).expanduser()
    p = p if p.is_absolute() else base / p
    if not p.is_file():
        raise InputError(f"Asset not found: {p}")
    if p.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise InputError("Only local PNG/JPEG/WebP assets are supported")
    return p.resolve()


def validate(data, base):
    if not isinstance(data, dict):
        raise InputError("Campaign input must be a JSON object")
    if not isinstance(data.get("brand"), dict) or not isinstance(data.get("events"), list) or not data["events"]:
        raise InputError("brand object and nonempty events list are required")
    brand = data["brand"]
    if not isinstance(brand.get("name"), str) or not brand["name"].strip():
        raise InputError("brand.name is required")
    for key, default in {"background": "#F2F0E9", "ink": "#172B28", "accent": "#D1EF70"}.items():
        brand[key] = color(brand.get(key, default))
    brand["font_regular"] = str(font_path(brand.get("font_regular"), base))
    bold = brand.get("font_bold")
    if not bold and "Arial.ttf" in brand["font_regular"]:
        bold = brand["font_regular"].replace("Arial.ttf", "Arial Bold.ttf")
    brand["font_bold"] = str(font_path(bold or brand["font_regular"], base))
    if brand.get("logo"):
        brand["logo"] = str(resolve_asset(brand["logo"], base))
    seen = set()
    for event in data["events"]:
        if not isinstance(event, dict):
            raise InputError("Each event must be an object")
        for key in ("id", "locale", "title", "date", "time", "timezone", "location", "cta"):
            if not isinstance(event.get(key), str) or not event[key].strip():
                raise InputError(f"Event requires nonempty {key}: {event.get('id')}")
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", event["id"]):
            raise InputError("Event id must be a filename-safe slug")
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", event["locale"]):
            raise InputError("Locale must be a filename-safe language tag")
        if (event["id"], event["locale"]) in seen:
            raise InputError("Duplicate event id + locale")
        seen.add((event["id"], event["locale"]))
        if event.get("family", "editorial") not in FAMILIES:
            raise InputError(f"Unknown family: {event.get('family')}")
        for key in ("subtitle", "edition", "category"):
            if key in event and not isinstance(event[key], str):
                raise InputError(f"{key} must be text")
        if "labels" in event and (not isinstance(event["labels"], list) or len(event["labels"]) != 3 or any(not isinstance(x, str) or not x.strip() for x in event["labels"])):
            raise InputError("labels must contain exactly three nonempty strings")
        try:
            datetime.fromisoformat(event["date"])
        except ValueError as exc:
            raise InputError("date must be ISO YYYY-MM-DD; time is a locked display string with timezone") from exc
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", event["date"]):
            raise InputError("date must be ISO YYYY-MM-DD")
        display_time = re.fullmatch(r"(\d{2}:\d{2}) ([A-Za-z0-9+:-]+)", event["time"])
        if not display_time:
            raise InputError("time must use HH:MM ZONE, for example 18:30 AEDT")
        try:
            local = datetime.fromisoformat(event["date"]+"T"+display_time[1]).replace(tzinfo=ZoneInfo(event["timezone"]))
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise InputError("Invalid time or IANA timezone") from exc
        candidates = [local.replace(fold=fold) for fold in (0, 1)]
        valid = [c for c in candidates if c.astimezone(timezone.utc).astimezone(c.tzinfo).replace(tzinfo=None) == local.replace(tzinfo=None)]
        if not valid:
            raise InputError("Local event time does not exist during a daylight-saving transition")
        if not any(c.tzname() == display_time[2] for c in valid):
            raise InputError(f"Time label {display_time[2]} does not match {event['timezone']} on {event['date']} ({local.tzname()}); confirm approved time")
        if event.get("image"):
            event["image"] = str(resolve_asset(event["image"], base))
        for key, length in (("focus", 2), ("protect", 4)):
            if key in event:
                values = event[key]
                if not isinstance(values, list) or len(values) != length or any(type(x) not in (float, int) or not 0 <= x <= 1 for x in values):
                    raise InputError(f"{key} must contain {length} normalised coordinates")
                if key == "protect" and (values[0] >= values[2] or values[1] >= values[3]):
                    raise InputError("protect box must have positive area")
    return data


@lru_cache(maxsize=32)
def glyphs(path):
    with TTFont(path, fontNumber=0) as font:
        return set(font.getBestCmap() or {})


@lru_cache(maxsize=32)
def family_name(path):
    with TTFont(path, fontNumber=0) as font:
        return font["name"].getDebugName(16) or font["name"].getDebugName(1) or Path(path).stem


@lru_cache(maxsize=32)
def font_weight(path):
    with TTFont(path, fontNumber=0) as font:
        return font["OS/2"].usWeightClass if "OS/2" in font else 400


def wrap(text, font, width):
    """Prefer word boundaries; break CJK and long tokens without deleting content."""
    if not text:
        return []
    lines = []
    for paragraph in text.split("\n"):
        tokens = re.findall(r"[\u2e80-\u9fff]|[^\S\n]+|[^\s\u2e80-\u9fff]+", paragraph)
        current = ""
        for token in tokens:
            candidate = current + token
            if font.getlength(candidate.rstrip()) <= width:
                current = candidate
                continue
            if current.strip():
                lines.append(current.rstrip())
                current = ""
            token = token.lstrip()
            for char in token:
                if current and font.getlength(current + char) > width:
                    lines.append(current)
                    current = ""
                current += char
        lines.append(current.rstrip())
    # Keep common CJK closing punctuation off a newly wrapped line, and do not
    # strand opening punctuation. Width is rechecked by the fitting loop.
    no_start = set("，。！？：；、）》】」』％%")
    no_end = set("（《【「『")
    for i in range(1,len(lines)):
        if lines[i] and lines[i][0] in no_start and len(lines[i-1]) > 1:
            moved = lines[i-1][-1]
            lines[i-1] = lines[i-1][:-1]
            lines[i] = moved + lines[i]
        if lines[i-1] and lines[i-1][-1] in no_end:
            moved = lines[i-1][-1]
            lines[i-1] = lines[i-1][:-1]
            lines[i] = moved + lines[i]
    return lines


class Scene:
    def __init__(self, width, height, bg, brand):
        self.w, self.h, self.bg, self.brand = width, height, bg, brand
        self.canvas = Image.new("RGB", (width, height), bg)
        self.draw = ImageDraw.Draw(self.canvas)
        self.elements, self.issues = [], []
        self.exclusions = []
        self.cm = {key: glyphs(brand[key]) for key in ("font_regular", "font_bold")}

    def rect(self, box, fill, radius=0):
        self.draw.rounded_rectangle(box, radius=radius, fill=fill)
        self.elements.append({"kind": "rect", "box": box, "fill": fill, "radius": radius})

    def ellipse(self, box, fill):
        self.draw.ellipse(box, fill=fill)
        self.elements.append({"kind": "ellipse", "box": box, "fill": fill})

    def text(self, role, text, box, max_size, min_size, fill, bold=False, max_lines=2, bg=None):
        key = "font_bold" if bold else "font_regular"
        missing = sorted({c for c in text if not c.isspace() and ord(c) not in self.cm[key]})
        if missing:
            raise InputError(f"{role}: font lacks glyphs {''.join(missing)!r}; provide a matching font")
        x, y, right, bottom = box
        for size in range(max_size, min_size - 1, -1):
            font = ImageFont.truetype(self.brand[key], size)
            lines = wrap(text, font, right - x)
            step = math.ceil(size * 1.13)
            if len(lines) <= max_lines and len(lines) * step <= bottom - y and all(font.getlength(s) <= right - x + .1 for s in lines):
                break
        else:
            raise InputError(f"{role}: content exceeds template capacity at readable minimum {min_size}px; shorten approved copy or change template")
        ratio = contrast(fill, bg or self.bg)
        if ratio < 4.5:
            self.issues.append({"level": "warning", "check": "contrast", "role": role, "ratio": round(ratio, 2), "message": "Below project text target 4.5:1; review actual viewing size"})
        for n, line in enumerate(lines):
            point = (x, y + n * step)
            self.draw.text(point, line, fill=fill, font=font, anchor="lt")
        self.elements.append({"kind": "text", "role": role, "text": text, "lines": lines, "box": box,
                              "ink_box": [x, y, x + max((font.getlength(s) for s in lines), default=0), y + len(lines) * step],
                              "font": self.brand[key], "size": size, "step": step, "fill": fill, "bold": bold})

    def image(self, role, path, box, focus=(.5, .5), protect=None, contain=False):
        source = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
        x, y, r, b = map(round, box)
        tw, th = r - x, b - y
        sw, sh = source.size
        scale = max(tw / sw, th / sh)
        cw, ch = tw / scale, th / scale
        left = min(max(focus[0] * sw - cw / 2, 0), sw - cw)
        top = min(max(focus[1] * sh - ch / 2, 0), sh - ch)
        crop = [left, top, left + cw, top + ch]
        if protect:
            p = [protect[0] * sw, protect[1] * sh, protect[2] * sw, protect[3] * sh]
            if p[0] < crop[0] or p[1] < crop[1] or p[2] > crop[2] or p[3] > crop[3]:
                contain = True
                self.issues.append({"level": "info", "check": "protected_crop", "role": role,
                                    "message": "Used contain to preserve supplied protected region"})
        if contain:
            crop = [0, 0, sw, sh]
            scale = min(tw / sw, th / sh)
            rw, rh = max(1, round(sw * scale)), max(1, round(sh * scale))
            tile = source.resize((rw, rh), Image.Resampling.LANCZOS)
            ox, oy = x + (tw - rw) // 2, y + (th - rh) // 2
        else:
            rw, rh, ox, oy = tw, th, x, y
            tile = source.crop(crop).resize((tw, th), Image.Resampling.LANCZOS)
        self.canvas.paste(tile, (ox, oy), tile)
        stream = io.BytesIO()
        tile.save(stream, format="PNG")
        self.elements.append({"kind": "image", "role": role, "box": [ox, oy, ox + rw, oy + rh], "source": str(path),
                              "crop": crop, "mode": "contain" if contain else "cover", "data": base64.b64encode(stream.getvalue()).decode()})
        effective = min(sw / rw, sh / rh) if contain else 1 / scale
        if effective < 1:
            self.issues.append({"level": "warning", "check": "image_resolution", "role": role, "message": "Source image is being enlarged"})

    def svg(self):
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">',
               f'<rect width="100%" height="100%" fill="{self.bg}"/>']
        for el in self.elements:
            x, y, r, b = el["box"]
            if el["kind"] == "rect":
                out.append(f'<rect x="{x}" y="{y}" width="{r-x}" height="{b-y}" rx="{el["radius"]}" fill="{el["fill"]}"/>')
            elif el["kind"] == "ellipse":
                out.append(f'<ellipse cx="{(x+r)/2}" cy="{(y+b)/2}" rx="{(r-x)/2}" ry="{(b-y)/2}" fill="{el["fill"]}"/>')
            elif el["kind"] == "image":
                out.append(f'<image x="{x}" y="{y}" width="{r-x}" height="{b-y}" href="data:image/png;base64,{el["data"]}"/>')
            else:
                name = escape(family_name(el["font"]), {'"': '&quot;'})
                for i, line in enumerate(el["lines"]):
                    out.append(f'<text x="{x}" y="{y+i*el["step"]}" dominant-baseline="text-before-edge" font-family="{name},sans-serif" font-size="{el["size"]}" font-weight="{font_weight(el["font"])}" fill="{el["fill"]}">{escape(line)}</text>')
        out.append("</svg>")
        return "\n".join(out)


def artwork(scene, box, family, ink, accent, paper):
    x, y, r, b = box
    width, height = r - x, b - y
    first = len(scene.elements)
    scene.rect(box, accent, 18)
    if family == "editorial":
        for i in range(7):
            cy = y + height * (.10 + i * .105)
            scene.ellipse([x + width * .16, cy, r - width * .16, cy + height * .24], ink)
            scene.ellipse([x + width * .26, cy + height * .025, r - width * .26, cy + height * .19], accent)
    elif family == "signal":
        columns, rows = (9, 2) if width / height > 2 else (3, 6)
        cell_w, cell_h = width / columns, height / rows
        for row in range(rows):
            for col in range(columns):
                cx, cy = x + cell_w*(col+.5), y + cell_h*(row+.5)
                rad = min(cell_w, cell_h) * (.24 if (row + col) % 3 else .39)
                scene.ellipse([cx-rad, cy-rad, cx+rad, cy+rad], ink)
    else:
        for i in range(9):
            xx = x + width * (.08 + i * .1)
            scene.rect([xx, y + height * .13, xx + width * (.026 if i % 2 else .05), b - height * .13], ink)
    for element in scene.elements[first:]:
        left, top, right, bottom = element["box"]
        if left < x or top < y or right > r or bottom > b:
            raise InputError(f"{family}: decorative artwork leaves its protected region")


def visual(scene, event, box, family, ink, accent, paper):
    if event.get("image"):
        scene.image("hero", event["image"], box, event.get("focus", [.5, .5]), event.get("protect"))
    else:
        artwork(scene, box, family, ink, accent, paper)
    scene.exclusions.append({"role": "hero", "box": box})


def editorial_layout(scene, event, size, footer, fg, ink, accent, paper):
    m, w = 64, scene.w
    wide = size == "wide"
    text_right = 1130 if wide else 666
    scene.text("category", event.get("category", "LIVE SESSION"), [m, 161, text_right, 203], 24, 18, fg, bold=True, max_lines=1)
    title_bottom = 575 if wide else min(610, footer - 190)
    scene.text("title", event["title"], [m, 225, text_right, title_bottom], 116 if wide else 96, 62, fg, bold=True, max_lines=4)
    if event.get("subtitle"):
        scene.text("subtitle", event["subtitle"], [m, title_bottom + 25, text_right - 20, footer - 32], 33, 25, fg, max_lines=3)
    art = [1220, 160, w-m, footer-32] if wide else [735, 166, w-m, footer-32]
    visual(scene, event, art, "editorial", ink, accent, paper)


def signal_layout(scene, event, size, footer, fg, ink, accent, paper):
    """Type-led announcement above a full-width visual, not a narrow side column."""
    m, w = 64, scene.w
    wide = size == "wide"
    scene.text("category", event.get("category", "LIVE SESSION"), [m, 159, w-m, 198], 24, 18, accent, bold=True, max_lines=1)
    if wide:
        scene.text("title", event["title"], [m, 225, 1260, 425], 112, 70, fg, bold=True, max_lines=2)
        if event.get("subtitle"):
            scene.text("subtitle", event["subtitle"], [1360, 233, w-m, 418], 34, 26, fg, max_lines=4)
        art = [m, 476, w-m, footer-32]
    else:
        title_bottom = 490 if size == "portrait" else 460
        scene.text("title", event["title"], [m, 225, w-m, title_bottom], 116, 66, fg, bold=True, max_lines=3)
        if event.get("subtitle"):
            scene.text("subtitle", event["subtitle"], [m, title_bottom+24, w-m, title_bottom+138], 34, 27, fg, max_lines=3)
        art = [m, title_bottom+172, w-m, footer-32]
    visual(scene, event, art, "signal", ink, accent, paper)


def ticket_layout(scene, event, size, footer, fg, ink, accent, paper):
    """Date-led event card with a date block and horizontal admission strip."""
    m, w = 64, scene.w
    wide = size == "wide"
    bx, br = (m, 450) if wide else (m, 334)
    badge_bottom = 580 if wide else 445
    scene.rect([bx, 164, br, badge_bottom], accent, 12)
    scene.text("date_day", event["date"][-2:], [bx+24, 195, br-24, 385 if wide else 332], 178 if wide else 128, 90, ink, bold=True, max_lines=1, bg=accent)
    scene.text("date_month", event["date"][:7], [bx+24, badge_bottom-78, br-24, badge_bottom-24], 37 if wide else 30, 24, ink, bold=True, max_lines=1, bg=accent)
    tx = 530 if wide else 390
    scene.text("category", event.get("category", "LIVE SESSION"), [tx, 167, w-m, 205], 24 if wide else 20, 16, fg, bold=True, max_lines=1)
    title_bottom = 520 if wide else 492
    scene.text("title", event["title"], [tx, 239, w-m, title_bottom], 110 if wide else 78, 60 if wide else 50, fg, bold=True, max_lines=3)
    if event.get("subtitle"):
        scene.text("subtitle", event["subtitle"], [tx, title_bottom+25, w-m, 655 if wide else 624], 34 if wide else 30, 25, fg, max_lines=3)
    art_top = 700 if wide else 673
    visual(scene, event, [m, art_top, w-m, footer-32], "ticket", ink, accent, paper)


def compose(data, event, size):
    w, h = SIZES[size]
    brand, family = data["brand"], event.get("family", "editorial")
    ink, paper, accent = brand["ink"], brand["background"], brand["accent"]
    bg, fg = (ink, paper) if family == "signal" else (paper, ink)
    scene = Scene(w, h, bg, brand)
    m, footer = 64, h - 222
    if brand.get("logo"):
        scene.image("logo", brand["logo"], [m, 54, m + 290, 108], contain=True)
    else:
        scene.text("brand", brand["name"], [m, 55, w - m - 240, 110], 36, 24, fg, bold=True, max_lines=1)
    scene.text("edition", event.get("edition", "SESSIONS / 2026"), [w - m - 240, 63, w-m, 105], 21, 16, fg, max_lines=1)
    scene.rect([m, 126, w-m, 128], fg)
    {"editorial": editorial_layout, "signal": signal_layout, "ticket": ticket_layout}[family](scene,event,size,footer,fg,ink,accent,paper)
    scene.rect([m, footer, w-m, footer+2], fg)
    cols = [m, m + (w-2*m)*.35, m + (w-2*m)*.69]
    widths = [(w-2*m)*.32, (w-2*m)*.31, (w-2*m)*.31]
    for role, label, value, x, width in zip(("date", "time", "location"), event.get("labels", ["DATE", "TIME", "WHERE"]),
                                            (event["date"], event["time"], event["location"]), cols, widths):
        scene.text(role+"_label", label, [x, footer+25, x+width, footer+55], 19, 16, fg, max_lines=1)
        scene.text(role, value, [x, footer+64, x+width, footer+145], 42, 30, fg, bold=True, max_lines=2)
    scene.rect([m, h-64, w-m, h-62], fg)
    scene.text("cta", event["cta"], [m, h-54, w-m, h-8], 34, 28, fg, max_lines=1)
    # Check text geometry and semantic retention independently of input validation.
    texts = [e for e in scene.elements if e["kind"] == "text"]
    for item in texts:
        x, y, r, b = item["ink_box"]
        if min(x, y) < 0 or r > w or b > h:
            raise InputError(f"{item['role']}: text leaves canvas")
        if "".join(item["lines"]).replace(" ", "") != item["text"].replace(" ", "").replace("\n", ""):
            raise InputError(f"{item['role']}: text changed during wrapping")
        for exclusion in scene.exclusions:
            a, b = item["ink_box"], exclusion["box"]
            if min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1]):
                raise InputError(f"Text overlaps protected visual: {item['role']} / {exclusion['role']}")
    for i, first in enumerate(texts):
        for second in texts[i+1:]:
            a, b = first["ink_box"], second["ink_box"]
            if min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1]):
                raise InputError(f"Text collision: {first['role']} / {second['role']}")
    return scene


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(source, output, sizes=None):
    source, output = Path(source).resolve(), Path(output).resolve()
    data = validate(read_json(source), source.parent)
    selected = sizes or list(SIZES)
    if any(s not in SIZES for s in selected) or len(set(selected)) != len(selected):
        raise InputError("Select unique sizes from square, portrait, wide")
    # Fail closed if stale files could be mistaken for this run.
    if output.exists() and any(output.iterdir()):
        raise InputError("Output directory must be empty; choose a new revision directory")
    scenes, failures = [], []
    for event in data["events"]:
        for size in selected:
            name = f"{event['id']}.{event['locale']}.{size}"
            try:
                scenes.append((name, event, size, compose(data, event, size)))
            except InputError as exc:
                failures.append({"item": name, "error": str(exc)})
    output.mkdir(parents=True, exist_ok=True)
    report = {"schema_version": 1, "source_sha256": sha(source), "expected": len(data["events"])*len(selected),
              "rendered": 0, "failed": failures, "items": [], "visual_review": "pending",
              "scope": "Geometry, retained source text, fonts, files, declared crop regions and simple solid-colour contrast. Not aesthetics, factual verification or platform approval."}
    thumbs = []
    for name, event, size, scene in scenes:
        png, svg = output / f"{name}.png", output / f"{name}.svg"
        scene.canvas.save(png)
        svg.write_text(scene.svg(), encoding="utf-8")
        source_file = output / f"{name}.scene.json"
        source_file.write_text(json.dumps({"canvas": [scene.w, scene.h], "background": scene.bg, "event": event,
                                         "elements": scene.elements}, ensure_ascii=False, indent=2), encoding="utf-8")
        with Image.open(png) as check:
            if check.size != SIZES[size]:
                raise InputError("Exported PNG dimension mismatch")
            check.verify()
        report["items"].append({"name": name, "size": SIZES[size], "png_sha256": sha(png), "svg_sha256": sha(svg),
                                "issues": scene.issues, "checks": {"png_decode": "pass", "text_retention": "pass", "text_geometry": "pass", "font_coverage": "pass"}})
        tile = Image.new("RGB", (380, 310), "#E1E4DF")
        thumb = scene.canvas.copy()
        thumb.thumbnail((350, 265))
        tile.paste(thumb, ((380-thumb.width)//2, 12))
        ImageDraw.Draw(tile).text((15, 285), name, fill="#172B28")
        thumbs.append(tile)
    if thumbs:
        columns = 3
        sheet = Image.new("RGB", (380*columns, 310*math.ceil(len(thumbs)/columns)), "#E1E4DF")
        for i, tile in enumerate(thumbs):
            sheet.paste(tile, ((i % columns)*380, (i//columns)*310))
        sheet.save(output / "contact-sheet.jpg", quality=90)
    report["rendered"] = len(scenes)
    report["status"] = "failed" if failures else ("review_required" if any(x["issues"] for x in report["items"]) else "technical_pass")
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "source.resolved.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    cards = "".join(f'<figure><a href="{html.escape(item["name"])}.svg"><img src="{html.escape(item["name"])}.png" alt="{html.escape(item["name"])}"></a><figcaption>{html.escape(item["name"])}</figcaption></figure>' for item in report["items"])
    (output / "index.html").write_text('<!doctype html><meta charset="utf-8"><title>Campaign proof</title><style>body{font:16px system-ui;background:#e1e4df;color:#172b28;margin:40px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:24px}figure{margin:0}img{width:100%;height:320px;object-fit:contain}figcaption{margin:12px}a{color:inherit}</style><h1>Campaign proof</h1><p>Technical checks are in report.json. Visual review is pending. SVG text requires matching local fonts; PNG is the delivery reference. Edit source.resolved.json and rebuild into a new revision.</p><main>'+cards+'</main>', encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--sizes", nargs="+", choices=list(SIZES))
    args = parser.parse_args()
    try:
        report = build(args.input, args.out, args.sizes)
        print(json.dumps({k: report[k] for k in ("status", "expected", "rendered", "failed")}, ensure_ascii=False))
        return 2 if report["failed"] else 0
    except (InputError, OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"campaign: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
