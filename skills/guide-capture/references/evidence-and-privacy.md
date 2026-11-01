# Evidence and privacy contract

Input JSON: title, audience, prerequisites, steps. Each step: unique id, action, expected, observed, screenshot path. Paths resolve relative to manifest. Origin is user-supplied (default), agent-observed or synthetic-demo. Agent-observed requires capture_note. This is provenance metadata, not a cryptographic proof or automated verification.

Optional redact/highlight lists contain [left,top,right,bottom] integer pixel boxes after EXIF rotation. Boxes must be inside the image and have positive area. Opaque redaction precedes highlights. Originals are never shipped; the report stores hashes, dimensions and annotation counts.

Builder does not detect private data, validate UI targets, redact prose or compare actual to expected. Inspect title, action, observed, capture notes and final pixels before sharing. Keep private manifests out of public repositories. Examples must not contain real credentials or personal data.

For live capture verify state transitions using permitted tools. Do not claim save/purchase/send/delete succeeded from a click alone. Missing evidence is a gap; do not invent a procedure. Publishing the guide requires separate authorization when it writes to an external destination.
