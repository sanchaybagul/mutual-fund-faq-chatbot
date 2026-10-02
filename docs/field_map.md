# Field Map: HDFC MF scheme page `__NEXT_DATA__` → SourceDoc

Produced by inspecting the 5 scheme-page snapshots in `data/raw/hdfc-*.json` (fetched 2026-10-02). `parse_scheme_page()` in `src/parser.py` follows this map. (The previous version of this file mapped the Groww pages used before the corpus moved to official sources.)

All paths are under `props.pageProps.singleFundResponse.data`. `details` is a list of one-key blocks; the parser merges them into one dict, so `details.Overview` means "the block whose key is `Overview`".

## Target fields

| Field | JSON path | Example (Small Cap) | Notes |
|---|---|---|---|
| `category` | `meta.category` + category from `sources.csv` | `Equity` – `Small Cap` | ELSS: `Tax Saver`; BAF: `Hybrid` |
| `expense_ratio` | `details.Overview.data.terDirecct` / `.terRegular` | `"0.79"` / `"1.56"` | Note the site's spelling `terDirecct`. Bare strings, so append `%`. This is the current total TER. |
| `exit_load` | `details.Overview.data.exitLoad` (HTML) | `In respect of each purchase / switch-in of Units, an Exit Load of 1.00% …` | ELSS: `NIL`. Strip HTML and `●` bullets. `exitLoadValue` is always null. |
| `min_sip` | `details.Overview.data.minimumSip` | `"100"` | ELSS: `500`. No lump-sum minimum on the page; the KIM has it. |
| `lock_in` | `details.Overview.data.lockInValue` | `null` | ELSS: `3 years`. Null means no lock-in. (`lockIn` is a generic tooltip, not the value.) |
| `riskometer` | `details.Overview.data.risk[0].name` | `Very High` | |
| `benchmark` | `details.Overview.data.benchmark[0]` | `BSE 250 SmallCap Index (Total Returns Index)` | |
| `aum` | `details.Overview.data.aum` + `.aumAsMonth` | `41,890.86` / `(31/08/2026)` | In ₹ crore, already formatted |
| `fund_managers` | `details.managers[].managerName` + `.since`; `details.overseasManagers[]` | `Mr. Chirag Setalvad` `(Since 2014)` | ⚠ `since` is `(Since 1970)` when the site has no date; drop it |
| `launch_date` | `details.Overview.data.inceptionDate` | `01/01/2013` | Direct Plan inception, not the scheme's |
| About text | `details.Overview.overviewDescription` (HTML) | | Cut at "Why invest" / "Who can consider" / "How to start" |
| FAQs | `details.faqs[]` (`title`, `description` HTML) | | Opinion-style FAQs are dropped (see below) |

## Quirks found

1. **The TER here differs from the factsheet.** The scheme page shows the current total TER (Small Cap Direct 0.79%), while the factsheet shows the *base* expense ratio as on month-end (0.72% on August 31, 2026), and the KIM shows FY 2024-25 actuals (Direct 1.10% for ELSS). Chunks label which figure is which.
2. **Fund manager dates use 1970 as a placeholder.** BAF's managers show `(Since 1970)`; the parser omits those dates.
3. **Some FAQs are opinions**, e.g. "SIP or lump sum: which is better?", "Can beginners invest?", "Is this fund risky?". FAQs whose titles match *should / suitable / who can / better / advantage / risky / beginners / ideal / role / why invest* are skipped. The scheme name is removed before matching so "Balanced **Advantage**" FAQs are kept.
4. **The "About" text includes marketing lines** such as "simple and performing scheme" and "30+ Years of Growth & Trust". Sentences that hint at performance are dropped.
5. **Keep these out of the corpus (PRD GR-2):**
   - `details.performanceDetails` / `performanceData`
   - `details.portfolio`, `top_10_holdings`, `market_segmentation`
   - `details.idcwData`
   - the "Returns since inception" figure on the page
6. **hdfcfund.com returns HTTP 403 to `requests` and curl.** It fingerprints the TLS handshake; the loader uses `curl_cffi` impersonating Chrome.

## Current values snapshot (2026-10-02, scheme pages)

| Scheme | TER (Direct) | Exit load | Min SIP | Lock-in | Risk | Benchmark |
|---|---|---|---|---|---|---|
| Large Cap | 1.04% | 1% if redeemed within 1 year | ₹100 | None | Very High | NIFTY 100 (Total Return Index) |
| Flexi Cap | 0.77% | 1% if redeemed within 1 year | ₹100 | None | Very High | NIFTY 500 Total Returns Index |
| ELSS Tax Saver | 1.21% | Nil | ₹500 | 3 years | Very High | NIFTY 500 Total Returns Index |
| Small Cap | 0.79% | 1% if redeemed within 1 year | ₹100 | None | Very High | BSE 250 SmallCap Index (TRI) |
| Balanced Advantage | 0.78% | 15% of units free; 1% on the rest within 1 year | ₹100 | None | Very High | NIFTY 50 Hybrid Composite Debt 50:50 Index |

## Other source types

| Source type | Parser | What is kept |
|---|---|---|
| `kim` | `parse_kim()` | KIM sections 2 (type), 5 (objective), 9 (plans/options), 11 (minimum application/redemption), 12 (redemption payout), 13 (benchmark), 19 (load structure and FY 2024-25 expenses), 23 (account statements, before the periodic-disclosure table). Skipped: asset allocation, strategy, risk profile, fund manager (dated; the scheme page is current), performance. |
| `factsheet` | `parse_factsheet()` | For each scheme, the labelled block on its first factsheet page: category, objective, fund managers, inception date, AUM, base expense ratio, benchmark, exit load. Skipped: NAV, risk ratios (standard deviation, beta, Sharpe), portfolio, performance tables. |
| `statement_guide`, `regulator` | `parse_guide()` | The article body between site-specific start/end markers (header and footer removed), with repeated paragraphs and form-widget labels dropped. |
