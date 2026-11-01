#!/usr/bin/env python3
"""Generate clearly synthetic UI fixtures, not evidence of a real app run."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "skills/guide-capture/assets"


def main():
    fp = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
    if not fp.exists():
        fp = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    def font(size):
        return ImageFont.truetype(str(fp), size)
    steps = []
    states = [("Open the event draft", "The draft shows its date and registration path.", "Draft details are visible; status is DRAFT."),
              ("Review the timezone", "The displayed time includes AEDT.", "The time field reads 18:30 AEDT."),
              ("Inspect the saved preview", "A saved status and event summary are visible.", "Synthetic preview displays SAVED and the event summary.")]
    for i, (action, expected, observed) in enumerate(states, 1):
        image = Image.new("RGB", (1400, 900), "#F2F0E9")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 250, 900), fill="#172B28")
        draw.text((28, 35), "FOUNDRY", font=font(27), fill="#D1EF70")
        draw.text((28, 120), "Events", font=font(22), fill="white")
        draw.text((28, 172), "Brand assets", font=font(22), fill="#ADBEB5")
        draw.text((310, 40), "SYNTHETIC DEMO / NOT A LIVE PRODUCT", font=font(18), fill="#596C62")
        draw.text((310, 105), "Event workspace", font=font(46), fill="#172B28")
        draw.rounded_rectangle((310, 205, 1320, 790), radius=20, fill="white")
        draw.text((350, 245), "Make room for better ideas.", font=font(36), fill="#172B28")
        for label, value, y in [("DATE", "2026-11-19", 345), ("TIME", "18:30 AEDT", 445), ("REGISTRATION", "foundry.example/build", 545)]:
            draw.text((350, y), label, font=font(16), fill="#596C62")
            draw.text((350, y+30), value, font=font(27), fill="#172B28")
        draw.text((350, 675), "Owner: demo@foundry.example", font=font(20), fill="#596C62")
        draw.rounded_rectangle((1090, 690, 1280, 750), radius=10, fill="#D1EF70")
        draw.text((1120, 706), "SAVED" if i == 3 else "DRAFT", font=font(24), fill="#172B28")
        filename = f"demo-step-{i}.png"
        image.save(DEST / filename)
        steps.append({"id":f"step-{i}","action":action,"expected":expected,"observed":observed,"screenshot":filename,
                      "origin":"synthetic-demo","redact":[[350,670,760,710]],"highlight":[[330,430,700,515]] if i == 2 else []})
    (DEST / "demo.json").write_text(json.dumps({"title":"Review an event before publishing","audience":"Fictional handover for an event coordinator.","prerequisites":"Synthetic screenshots only; no successful live workflow is demonstrated.","steps":steps}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
