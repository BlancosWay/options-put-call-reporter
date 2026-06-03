# Daily Options Put/Call Report Design

## Goal

Build a local automation that analyzes Barchart put/call ratio pages every trading day and emails a detailed report after market close.

The report should cover the current watchlist:

- META: `https://www.barchart.com/stocks/quotes/meta/put-call-ratios`
- GOOG: `https://www.barchart.com/stocks/quotes/goog/put-call-ratios`
- MSFT: `https://www.barchart.com/stocks/quotes/msft/put-call-ratios`
- NFLX: `https://www.barchart.com/stocks/quotes/nflx/put-call-ratios`
- NOW: `https://www.barchart.com/stocks/quotes/now/put-call-ratios`
- AAOI: `https://www.barchart.com/stocks/quotes/aaoi/put-call-ratios`
- LITE: `https://www.barchart.com/stocks/quotes/lite/put-call-ratios`

The project will live at:

`/Users/sri/personal/options-put-call-reporter`

## Schedule

The daily job should run after market close at approximately **5:30 PM ET**. On the current machine this corresponds to **2:30 PM Pacific Time**.

The report should also support a manual command so the user can run the analysis on demand before enabling the scheduled job.

## Architecture

The system has six components:

1. **Configuration**
   - Stores symbols, Barchart URLs, report time, recipient email, archive path, and signal thresholds.
   - Does not store secrets.

2. **Browser collector**
   - Opens each Barchart put/call page in a headless browser.
   - Waits for the live table and top metrics to load.
   - Extracts earnings date, implied volatility, historic volatility, IV rank, IV percentile, and expiration table rows.
   - Saves raw extracted data before analysis.
   - Saves screenshots or HTML snapshots when extraction fails.

3. **History store**
   - Persists one dated snapshot per symbol per run.
   - Stores top metrics, raw expiration rows, derived monthly signals, and run metadata.
   - Supports comparisons against the nearest prior saved trading snapshots for previous day, previous week, and previous month.

4. **Analyzer**
   - Normalizes expiration rows into monthly buckets.
   - Keeps the monthly/major expirations needed for a one-year view.
   - Classifies each month as strong bullish, bullish, neutral, mixed, bearish, or hedging-heavy.
   - Generates day/week/month drift commentary.

5. **Report generator**
   - Creates a detailed HTML email.
   - Archives HTML, Markdown, and CSV/JSON data locally for each run.

6. **Email sender**
   - Sends the report through Gmail SMTP.
   - Reads the Gmail App Password from macOS Keychain at runtime.
   - Never stores Gmail credentials in the project files.

## Signal methodology

The first version should use configurable thresholds based on put/call volume ratio and put/call open-interest ratio:

- Lower put/call ratios generally indicate more call-heavy, bullish positioning.
- Higher put/call ratios generally indicate more put-heavy, defensive, bearish, or hedging-heavy positioning.
- Volume ratio reflects current-session flow and should be treated as the faster-moving signal.
- Open-interest ratio reflects accumulated positioning and should be treated as the slower-moving confirmation or hedging signal.

Initial classification rules should be evaluated in order:

| Condition | Signal |
|---|---|
| Volume ratio <= 0.35 and OI ratio <= 0.70 | Strong bullish |
| Volume ratio < 0.70 and OI ratio < 0.90 | Bullish |
| Volume ratio > 1.10 or OI ratio > 1.25 | Bearish / hedging-heavy |
| Volume ratio < 0.70 and OI ratio between 1.00 and 1.25 | Mixed / caution |
| Volume ratio between 0.70 and 1.10 and OI ratio below 1.10 | Neutral |
| Any remaining conflicting signals | Mixed |

These thresholds should be stored in config so they can be adjusted after reviewing live output.

## Drift analysis

Each daily report should explain what changed compared with the nearest prior saved trading snapshots:

- **Previous day:** most recent successful prior run.
- **Previous week:** nearest saved run around five trading days back.
- **Previous month:** nearest saved run around 21 trading days back.

For each symbol, the report should show:

- changes in implied volatility, IV rank, and IV percentile
- changes in put/call volume ratio by monthly expiration
- changes in put/call open-interest ratio by monthly expiration
- signal flips, such as bullish to bearish or mixed to bullish
- months where hedging increased or decreased
- number of bullish, neutral, mixed, and bearish months now versus prior periods

The commentary should focus on meaningful changes and avoid overstating noise from tiny-volume expirations.

## Report content

The email should include:

1. **Executive summary**
   - Overall watchlist tone.
   - Best bullish setups.
   - Weakest or most hedged setups.
   - Biggest day/week/month changes.

2. **Per-symbol section**
   - Current top metrics.
   - One-year monthly signal table.
   - Day/week/month drift summary.
   - Commentary explaining whether the current setup is bullish, bearish, mixed, or cautionary.
   - Raw expiration table.

3. **Failure section**
   - Any symbol that failed extraction.
   - Error summary and path to saved diagnostic screenshot/HTML.

4. **Archive details**
   - Local paths to the saved report and raw data.

## Storage

The local archive should be organized by date:

`/Users/sri/personal/options-put-call-reporter/archive/YYYY-MM-DD/`

Each run should save:

- raw extracted JSON per symbol
- normalized CSV per symbol
- generated Markdown report
- generated HTML email
- diagnostic screenshots/HTML only when needed

The history store can be SQLite or structured JSON files. SQLite is preferred because it simplifies nearest-prior snapshot queries.

## Security

Secrets must not be committed or stored in config files.

The Gmail App Password should be stored in macOS Keychain under a clear service name such as:

`options-put-call-reporter:gmail-app-password`

The implementation should document the Keychain setup command and should fail clearly if the credential is missing.

## Error handling

The job should not silently hide failures.

Expected behavior:

- If one symbol fails, continue with the remaining symbols and mark the failed symbol in the email.
- If all symbols fail, do not send a success-shaped report; send or save a failure report that states no usable data was collected.
- If Barchart changes the page layout, preserve the diagnostic artifacts needed to fix extraction.
- If email sending fails, keep the generated report and raw data locally and print a clear error.

## Testing and validation

Implementation should include validation for:

- extraction from every configured Barchart URL
- parsing and normalization of expiration rows
- monthly signal classification thresholds
- nearest prior snapshot selection for day/week/month drift
- report generation with complete and partial data
- Gmail sender behavior when Keychain credential is present or missing

Before enabling the scheduler, the manual run command should produce a complete local report for the full seven-symbol watchlist.

## Out of scope for the first version

- Trading recommendations or automated trade execution.
- A web dashboard.
- Paid data-provider integration.
- Intraday alerts.
- Backtesting trading strategies.
