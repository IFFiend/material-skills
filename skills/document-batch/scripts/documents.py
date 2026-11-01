#!/usr/bin/env python3
"""Generate auditable quote HTML from integer minor units; standard library only."""
from __future__ import annotations
import argparse
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import html
import json
import re
import sys
from datetime import date
from pathlib import Path


class DocumentError(ValueError):
    pass


def esc(value):
    return html.escape(str(value), quote=True)


def calculate(quote):
    if not isinstance(quote.get("lines"), list) or not quote["lines"]:
        raise DocumentError("Each quote requires at least one line")
    amounts = []
    for line in quote["lines"]:
        if not isinstance(line, dict):
            raise DocumentError("Each quote line must be an object")
        if not isinstance(line.get("description"), str) or not line["description"].strip():
            raise DocumentError("Every line requires a description")
        if type(line.get("unit_minor")) is not int or line["unit_minor"] < 0:
            raise DocumentError("unit_minor must be a non-negative integer, never a floating-point price")
        if not isinstance(line.get("quantity"), str):
            raise DocumentError("quantity must be a decimal string")
        try:
            q = Decimal(line["quantity"])
            if not q.is_finite() or q <= 0 or q > Decimal("1000000000"):
                raise DocumentError("Quantity must be positive, finite and <= 1 billion")
            amount = int((q * line["unit_minor"]).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        except InvalidOperation as exc:
            raise DocumentError("Invalid decimal quantity") from exc
        amounts.append(amount)
    if "tax_bps" not in quote:
        raise DocumentError("tax_bps is required; do not infer a zero tax rate")
    bps = quote["tax_bps"]
    if type(bps) is not int or not 0 <= bps <= 10000:
        raise DocumentError("tax_bps must be an integer from 0 to 10000; rate is user-supplied")
    subtotal = sum(amounts)
    tax = int((Decimal(subtotal) * Decimal(bps) / 10000).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    return {"line_minor": amounts, "subtotal_minor": subtotal, "tax_minor": tax, "total_minor": subtotal+tax,
            "policy": "Round each line to integer minor units, then tax on subtotal, ROUND_HALF_UP"}


def money(minor, currency):
    return f"{currency} {minor//100:,}.{minor%100:02}"


def build(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise DocumentError("Input must be a JSON object")
    if not isinstance(data.get("issuer"), dict) or not data["issuer"].get("name") or not data["issuer"].get("contact"):
        raise DocumentError("issuer.name and issuer.contact are required")
    quotes = data.get("quotes")
    if not isinstance(quotes, list) or not quotes:
        raise DocumentError("quotes must be a nonempty list")
    if output.exists() and any(output.iterdir()):
        raise DocumentError("Use an empty output directory")
    seen, prepared = set(), []
    for quote in quotes:
        if not isinstance(quote, dict):
            raise DocumentError("Each quote must be an object")
        for field in ("id", "client", "title", "date", "valid_until", "currency", "terms"):
            if not isinstance(quote.get(field), str) or not quote[field].strip():
                raise DocumentError(f"Quote missing {field}")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", quote["id"]) or quote["id"] in seen:
            raise DocumentError("Quote id must be a unique filename-safe slug")
        seen.add(quote["id"])
        # Explicitly limited to two-decimal currencies; no guessed tax law or FX.
        if quote["currency"] not in {"AUD", "USD", "EUR", "GBP", "CAD", "NZD", "SGD", "CNY", "HKD"}:
            raise DocumentError("Unsupported currency exponent; this renderer supports listed two-decimal currencies only")
        if date.fromisoformat(quote["valid_until"]) < date.fromisoformat(quote["date"]):
            raise DocumentError("valid_until precedes quote date")
        totals = calculate(quote)
        for name in ("subtotal_minor", "tax_minor", "total_minor"):
            if name in quote and (type(quote[name]) is not int or quote[name] != totals[name]):
                raise DocumentError(f"Supplied {name} does not match independently calculated amount")
        prepared.append((quote, totals))
    output.mkdir(parents=True, exist_ok=True)
    report = {"schema_version": 1, "status": "technical_pass", "visual_review": "pending", "pdf": "not_generated",
              "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "items": [],
              "scope": "Arithmetic and source fields only; tax rules, contract terms and customer facts are not verified"}
    css = 'body{background:#e8eae4;color:#172b28;font:15px/1.5 system-ui;margin:0}.page{max-width:920px;margin:48px auto;background:#fff;padding:60px}header{display:flex;justify-content:space-between;border-bottom:2px solid;padding-bottom:25px}.label{font:12px monospace;letter-spacing:1px;color:#596c62}h1{font-size:42px;line-height:1.1;margin:32px 0}table{border-collapse:collapse;width:100%;margin:32px 0}th{text-align:left;font-size:12px;text-transform:uppercase}td,th{padding:14px 8px;border-bottom:1px solid #dfe4dc}td.num,th.num{text-align:right;white-space:nowrap}.totals{margin-left:auto;max-width:350px}.total{font-size:23px;font-weight:700;background:#d1ef70;padding:16px}footer{margin-top:48px;border-top:1px solid #dfe4dc;padding-top:20px}tr{break-inside:avoid}thead{display:table-header-group}@media print{@page{size:A4;margin:16mm}body{background:white}.page{margin:0;padding:0;max-width:none}h1{font-size:30px}.totals,footer{break-inside:avoid}}'
    css += '.table-scroll{max-width:100%;overflow-x:auto}.table-note{display:none}header>div{min-width:0;overflow-wrap:anywhere}@media(max-width:700px){.page{margin:12px;padding:24px}header{flex-wrap:wrap;gap:20px}h1{font-size:30px;overflow-wrap:anywhere}table{min-width:580px}.table-note{display:block;color:#596c62;font-size:12px}footer{overflow-wrap:anywhere}.total{font-size:21px}}@media print{.table-scroll{overflow:visible}.table-note{display:none}table{min-width:0}}'
    for quote, totals in prepared:
        currency = quote["currency"]
        rows = "".join(f'<tr><td>{esc(line["description"])}</td><td class="num">{esc(line["quantity"])}</td><td class="num">{money(line["unit_minor"],currency)}</td><td class="num">{money(amount,currency)}</td></tr>' for line, amount in zip(quote["lines"], totals["line_minor"]))
        doc = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{esc(quote["id"])}</title><style>{css}</style></head><body><article class="page"><header><div><strong>{esc(data["issuer"]["name"])}</strong><br>{esc(data["issuer"]["contact"])}</div><div class="label">QUOTE / {esc(quote["id"])}<br>{esc(quote["date"])}</div></header><h1>{esc(quote["title"])}</h1><p><span class="label">PREPARED FOR</span><br>{esc(quote["client"])}</p><p>Valid until {esc(quote["valid_until"])}</p><table><thead><tr><th>Description</th><th class="num">Qty</th><th class="num">Unit</th><th class="num">Amount</th></tr></thead><tbody>{rows}</tbody></table><div class="totals"><p>Subtotal: {money(totals["subtotal_minor"],currency)}</p><p>Tax ({quote.get("tax_bps",0)/100:g}%): {money(totals["tax_minor"],currency)}</p><p class="total">Total: {money(totals["total_minor"],currency)}</p></div><footer><span class="label">TERMS</span><p>{esc(quote["terms"])}</p><p class="label">Prepared from supplied data. Not an invoice or a signed agreement.</p></footer></article></body></html>'
        doc = doc.replace("<table>", '<p class="table-note">Swipe to view quantities and prices →</p><div class="table-scroll" role="region" aria-label="Quote line items; scroll horizontally on small screens" tabindex="0"><table>').replace("</table>", "</table></div>")
        path = output / f"{quote['id']}.html"
        path.write_text(doc, encoding="utf-8")
        record = {"input": quote, "calculated": totals}
        (output / f"{quote['id']}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        report["items"].append({"id": quote["id"], "calculated": totals, "html_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    links = "".join(f'<li><a href="{esc(q["id"])}.html">{esc(q["id"])} — {esc(q["title"])}</a></li>' for q, _ in prepared)
    (output / "index.html").write_text(f'<!doctype html><meta charset="utf-8"><title>Quote batch</title><style>body{{font:18px system-ui;max-width:900px;margin:60px auto;color:#172b28}}li{{margin:20px}}</style><h1>Quote batch</h1><p>Arithmetic checked. Visual review pending; PDF export has not been performed.</p><ul>{links}</ul>', encoding="utf-8")
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(args.input, args.out)
        print(json.dumps({"status": result["status"], "documents": len(result["items"]), "pdf": result["pdf"]}))
        return 0
    except (DocumentError, OSError, ValueError, TypeError, KeyError) as exc:
        print(f"documents: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
