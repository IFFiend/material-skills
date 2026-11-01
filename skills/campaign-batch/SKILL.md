---
name: campaign-batch
description: Produce and check batches of branded event graphics from approved copy and local assets. Use for event announcements in square, portrait and wide formats, not brand identity design, product photography or app-store screenshots.
license: PolyForm Noncommercial 1.0.0
---

# Campaign Batch

Deliver PNG graphics, editable SVG and input JSON, a contact sheet, and an item-level technical report. Three original layout families adapt to three aspect ratios: editorial sidebar, full-width signal and date-first ticket. Do not describe this as a complete marketing suite or an unconstrained designer.

## Establish the brief

Read [design decisions](references/design-decisions.md) for treatment selection and overflow repair; read [input contract](references/input-contract.md) when constructing input. Use actual brand rules ahead of defaults. Separate approved facts from proposed copy. Dates, times, locations and identifiers are locked; write language variants explicitly rather than translating inside the renderer.

Inspect the supplied logo and images. Set a focal point and protected rectangle if a face or label must survive cropping. The script falls back to contain when that rectangle would be cropped; it does not detect subjects.

License: [PolyForm Noncommercial 1.0.0](LICENSE).

## Produce a proof

Requirements: Python 3.10+, Pillow and fonttools. If missing, install with `python -m pip install 'Pillow>=11,<14' 'fonttools>=4.50,<5'` when authorized. No API key or browser is required.

From this skill directory:

```sh
python scripts/campaign.py assets/demo.json --out /tmp/campaign-proof
python scripts/campaign.py /absolute/path/campaign.json --out /absolute/path/revision-01
```

Output must be empty. Use `--sizes square` for a single-format proof. Paths in input resolve relative to that JSON. Fonts are supplied or resolved from a system font; no fonts are redistributed. Editable SVG depends on matching installed fonts. PNG is the delivery reference.

Render a representative input first, inspect the actual PNG, then produce the approved batch. Never change locked facts, silently truncate, or shrink below the template floor to pass. Change composition, request approved shorter copy, or report the item as failed.

## Inspect the result

Read report.json, inspect contact-sheet.jpg, then inspect the longest-title item and every image/crop variant at full and phone viewing size. Review all nine treatment/ratio combinations when introducing a new brand. Report warnings and failed items separately; missing files mean an incomplete batch.

The script checks glyphs, retained text, text collisions/bounds, PNG decoding/dimensions and simple solid-background contrast. It does not establish factual accuracy, asset rights, platform approval, creative quality or conversion.

Report technical and visual review separately. A script technical_pass leaves visual_review pending; never invent an aesthetic score. Deliver sources and report beside final files. Do not publish externally without authorization.
