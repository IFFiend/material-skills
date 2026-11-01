# Evaluation protocol

Status: defined, **not executed as a controlled model comparison**. Unit tests and screenshots do not prove the skill beats prompting. Publish no win rate without the underlying runs.

## Conditions

Compare the user's ordinary prompt, a strong general prompt (below), and the full skill. Add a template-and-script-only ablation to measure whether the instructions add value. Use the same model version, raw inputs, tools, permissions and time budget. Baselines may write code and check their outputs; do not restrict them to raster generation. Record skill resources as part of the product advantage. Randomize order, blind reviewers, record all prompts, versions, manual edits and costs if known.

## Campaign

At least 12 held-out briefs: short/long titles, three aspect ratios, photo crop protection, dark/light brands, missing glyphs, supplied translations, missing fields, DST time labels, and changes to date/image. Use at least two repetitions per condition. Include unfamiliar brands with permission, not only demos tuned with the templates.

Strong baseline prompt:

> Produce a consistent set of event graphics using the provided brand and approved facts. Give each aspect ratio an intentional layout, keep locked facts unchanged, preserve image subjects and maintain readable type at the stated display size. Supply PNGs and editable sources. Inspect final renders for missing text, crop errors, overlaps and poor readability. Report unresolved problems rather than silently altering facts. You may write code and use available tools within the time budget.

Measure exact locked-field errors, missing exports, observable render defects, hierarchy, brand consistency, manual correction time and update time. Have target users and a design reviewer judge at the same display sizes. Report ties, sample sizes and uncertainty. The renderer's own checks cannot be the only aesthetics judge.

Proposed gate: no altered locked fields; fewer defects and materially less manual correction than the strong prompt; no meaningful visual-quality regression. These are intended gates, **not achieved findings**.

## Other skills

Guides: distinguish live-observed and supplied evidence. Check transitions, actual privacy masks, unresolved outcomes, link portability and editing time. Synthetic fixtures do not count as live capture.

Quotes: externally calculated amounts, fractional quantities, rounding boundaries, client separation, incorrect supplied totals and long tables. Check printed pages if PDF is in the task. Arithmetic is not tax validation.

## Auditable records

One JSON record per run: task_id, condition, model/version, skill_commit, started_at, elapsed_seconds, manual_minutes, optional tool_cost, output_files, exact_field_errors, missing_exports, observed_defects, reviewer_votes and unresolved. Keep sanitized raw inputs and outputs. Missing evaluation remains missing, never zero errors by default.
