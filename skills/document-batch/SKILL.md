---
name: document-batch
description: Generate checked batches of editable quotations from structured client data, decimal quantities and integer prices. Use for quotes and estimates with explicit rates, not invoices, signatures, tax advice or generic reports.
license: PolyForm Noncommercial 1.0.0
---

# Document Batch

Generate quotation HTML, auditable calculation JSON and a batch index. This edition supports quotations only, not contracts, signatures, automatic sending or verified PDF output.

## Establish the source

Read [calculation contract](references/calculation-contract.md). Obtain issuer/client mapping, quote identifiers, validity dates, currency, approved scope/terms, quantities and prices. Do not infer tax rules, legal wording or bank information.

Use integer minor-unit prices and decimal-string quantities. Only listed two-decimal currencies are supported. Supply tax basis points explicitly: zero means a known zero rate, not an unknown rate. Confirm a different rounding policy instead of silently adapting.

## Build

Requirements: Python 3.10+, standard library only. From this skill directory:

```sh
python scripts/documents.py assets/demo.json --out /tmp/quote-proof
python scripts/documents.py /absolute/path/quotes.json --out /absolute/path/quotes-revision-01
```

Output must be empty. Whole input is validated first. Supplied totals must agree with recalculation; fix actual errors, never remove supplied totals just to pass.

## Verify and deliver

Read report.json and inspect every HTML document, line table, scope and terms. Check client mappings/dates against sources. Long descriptions and many-line documents require full review.

Builder does not render PDF. If requested, use an available PDF workflow and render every page; inspect splits, totals, fonts and headers. Deliver editable sources too. Arithmetic proof is not tax/legal validation or client approval.

Do not send documents or create signatures without explicit instructions.

License: [PolyForm Noncommercial 1.0.0](LICENSE).
