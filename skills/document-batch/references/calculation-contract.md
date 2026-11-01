# Quotation calculation contract · v0.1

assets/demo.json uses fictional names, prices and work. Tax rates are supplied, not advice.

Issuer requires name/contact. Quotes require unique filename-safe id, client, title, ISO date, valid_until, currency, terms and lines. Each line: description, decimal-string quantity, nonnegative integer unit_minor. Supported two-decimal currencies: AUD, USD, EUR, GBP, CAD, NZD, SGD, CNY, HKD. Other exponents require explicit support.

1. Line = quantity × unit_minor, rounded to integer minor units with decimal ROUND_HALF_UP.
2. Subtotal = sum of rounded line amounts.
3. Tax = subtotal × tax_bps / 10000, rounded once with ROUND_HALF_UP.
4. Total = subtotal + tax.

1000 basis points means 10%. tax_bps is mandatory: provide zero only for an explicitly known zero rate. Positive finite quantities only. Credits, discounts, compound/inclusive tax, FX and legal invoice fields are outside scope.

Optional supplied subtotal_minor/tax_minor/total_minor values must match exactly or the whole batch is blocked. Outputs expose calculated integers and policy. Arithmetic does not prove lawful tax treatment, correct client mapping or printed page layout.
