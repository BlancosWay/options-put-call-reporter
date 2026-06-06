# yfin Fallback Data Source Design

## Goal

Keep Barchart as the primary data source, but preserve usable reports when Barchart collection breaks by falling back to free yfin.dev options-chain data. Every generated artifact must disclose the source used for each symbol and whether that source was a fallback.

## Architecture

`collector.collect_symbol()` remains the public collection entry point. It first attempts the existing Barchart Playwright/network flow. If that raises `CollectionError`, it fetches yfin.dev option-chain JSON, aggregates calls and puts by expiration, and returns a `Snapshot` marked as fallback-sourced.

Snapshots carry a small `DataSource` value with provider name, provider URL, fallback flag, and a short note. Reporting reads that metadata and writes it into HTML, Markdown, and raw expiration CSV files. History persistence stores the metadata for new snapshots and defaults old rows to Barchart metadata when loading databases created before this feature.

## yfin Aggregation

The fallback calls `https://api.yfin.dev/v1/options?symbol={SYMBOL}` to get expiration dates and the nearest chain. It then calls the same endpoint with `date={unix_expiration}` for remaining expirations. For each expiration:

- Put volume is the sum of put contract `volume`.
- Call volume is the sum of call contract `volume`.
- Put open interest is the sum of put contract `openInterest`.
- Call open interest is the sum of call contract `openInterest`.
- Total volume and total open interest are computed from those sums.
- Put/call ratios are computed from the aggregated totals. When the denominator is nonzero, the ratio is numerator divided by denominator. When both numerator and denominator are zero, the ratio is `0.0`; when the numerator is positive and the denominator is zero, the in-memory ratio is `float("inf")` so put-heavy zero-call data remains bearish/hedging-heavy downstream. Diagnostic JSON emitted by Python may serialize that value as `Infinity`.
- Implied volatility is the arithmetic average of contract `impliedVolatility` values converted from decimal form to percent.
- Expirations on the standard monthly expiration date are marked monthly; other expirations are weekly.

yfin does not provide Barchart-equivalent top metrics such as IV Rank and IV Percentile. Fallback snapshots set unavailable top metrics to `None`, while preserving aggregated expiration rows for signal generation.

## Error Handling

If Barchart fails and yfin succeeds, the run continues and the report states that yfin.dev fallback data was used after Barchart failed. If both fail, the symbol remains a failure and the error message includes both the Barchart and yfin causes. The fallback should not silently produce an empty snapshot: zero aggregated rows is a collection error.

## Testing

Tests cover:

- yfin JSON aggregation into expiration rows and fallback source metadata.
- Barchart failure falling back to yfin and archiving yfin raw/snapshot JSON.
- yfin failure surfacing both primary and fallback errors.
- report HTML, Markdown, and CSV source disclosure.
- history round-trip of `DataSource` metadata.
