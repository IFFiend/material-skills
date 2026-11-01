---
name: guide-capture
description: Turn observed browser workflows or ordered user screenshots into redacted, evidence-labelled guides with portable HTML and Markdown. Use for onboarding and client handovers, not inferred procedures or unattended monitoring.
license: PolyForm Noncommercial 1.0.0
---

# Guide Capture

Produce a guide tied to screenshots and observed outcomes. The builder assembles and checks supplied evidence; **it does not capture a workflow or prove actions succeeded**.

## Gather evidence

Use the user's selected browser/app tools for authorized workflows. Documentation does not authorize sending, buying, deleting or changing a live account. Supplied screenshots are sufficient when labelled user-supplied; do not assert live verification.

For each step record action, expected outcome, observed state and screenshot. Mark agent-observed only after actual observation, with a capture note naming the surface/session and result. Mark included fixtures synthetic-demo. Never describe an expected outcome as observed merely because its button exists.

Read [evidence and privacy](references/evidence-and-privacy.md). Ask for missing evidence rather than inventing a step.

## Build

Requirements: Python 3.10+ and Pillow. From this skill directory:

```sh
python scripts/guide.py assets/demo.json --out /tmp/guide-proof
python scripts/guide.py /absolute/path/guide.json --out /absolute/path/guide-revision-01
```

Coordinates are screenshot pixels after EXIF rotation. Review screenshots first; specify opaque redaction boxes for sensitive areas. Exported images contain irreversible redactions; originals are not copied. The manifest may contain private prose and is intentionally not copied.

Outputs: index.html, guide.md, images/, report.json. The script does not automatically detect private data or export PDF. If PDF is requested, use an available document workflow and render/verify separately.

## Acceptance

Inspect every exported screenshot, annotation, redaction and outcome, plus prose for private information. Check prerequisites, start/end state, missing transitions and stable action targets. Move the output folder and verify HTML/Markdown image links.

Report technical export, privacy review and observation separately. Builder always reports behavioral_verification: not_performed_by_builder. Claim observation only for steps actually observed; it is not proof of future compatibility or all account states.

License: [PolyForm Noncommercial 1.0.0](LICENSE).
