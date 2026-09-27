# Field Map: Groww `__NEXT_DATA__` → SchemeDoc

Produced during Phase 1 by inspecting the 5 snapshots in `data/raw/*.json` (fetched 2026-09-27). Phase 2 (`src/parser.py`) uses this as its `FIELD_PATHS` reference.

All fields below are under `props.pageProps.mfServerSideData` (referred to as `m`).

## Target fields

| Field | JSON path | Example (Small Cap) | Notes |
|---|---|---|---|
| `scheme_name` | `m.scheme_name` | `HDFC Small Cap Fund Direct Growth` | |
| `fund_house` | `m.fund_house` | `HDFC Mutual Fund` | |
| `category` | `m.category` + `m.sub_category` | `Equity` / `Small Cap` | BAF: `Hybrid` / `Dynamic Asset Allocation` |
| `expense_ratio` | `m.expense_ratio` | `"0.78"` | A bare string, so append `%` |
| `exit_load` | `m.exit_load` | `Exit load of 1% if redeemed within 1 year` | ELSS: `Nil`. Flexi Cap has a trailing `\n`, so strip it. |
| `min_sip` | `m.min_sip_investment` | `100` | An int, so format as `₹100`. ELSS: `500`. |
| `min_lumpsum` | `m.min_investment_amount` | `100` | ELSS: `500` |
| `min_additional` | `m.mini_additional_investment` | `100` | |
| `lock_in` | `m.lock_in` → `{years, months, days}` | all `null` | ELSS: `{years: 3, months: 0, days: 0}`, which should read "3 years". All nulls mean no lock-in. |
| `riskometer` | **`m.return_stats[0].risk`** | `Very High` | ⚠ See the quirks below |
| `benchmark` | `m.benchmark_name` (full) / `m.benchmark` (short) | `BSE 250 SmallCap Total Return Index` / `BSE 250 SmallCap TRI` | |
| `aum` | `m.aum` | `41890.8613` | In ₹ crore. Format as `₹41,890.86 Cr`. |
| `fund_managers` | `m.fund_manager_details[].person_name` (+ `date_from`, `education`, `experience`) | Dhruv Muchhal, Chirag Setalvad | ⚠ Use the list, not `m.fund_manager` |
| `launch_date` | `m.launch_date` | `01-Jan-2013` | This is the Direct plan launch |
| `objective` | `m.description` | `The scheme seeks to provide long-term capital appreciation…` | |
| `stamp_duty` | `m.stamp_duty` | `0.005% (from July 1st, 2020)` | |
| `tax_note` | `m.category_info.tax_impact` | `If you redeem within one year, returns are taxed at 20%…` | Generic equity tax text |
| `rta` | `m.rta_details.rta_name` / `.website` | `Cams` / `www.camsonline.com` | Useful for "how to download a statement" (the statement is issued by the RTA) |
| `sid_url` | `m.sid_url` | `https://www.hdfcfund.com` | Only the AMC homepage, not a deep link |
| `plan_type` | `m.plan_type` | `Direct` | |

## Quirks found (important for Phase 2)

1. **`m.nfo_risk` is stale.** It says "Moderately High" for all 5 schemes, while the page displays **"Very High Risk"**. Use `m.return_stats[0].risk`, which matches the page for all 5.
2. **`m.category_info.sub_type` / `category_helper_text` is wrong.** It says "Contra" for all 5 schemes. Ignore it and use `m.sub_category`.
3. **`m.fund_manager` lists only one name.** `m.fund_manager_details` has the full current list: 2 managers for most schemes and 6 for BAF.
4. **The HTML "About" prose mixes AMC-level and fund-level data.** It gives AUM as "₹9,86,237 Cr" and the launch date as "10 Dec 1999", which are the **AMC's** figures, not the fund's. Take facts from the JSON, not that paragraph.
5. **Keep these return and performance fields out of the corpus (PRD GR-2):**
   - `stats`
   - `return_stats` (except `.risk`)
   - `sip_return`, `simple_return`
   - `analysis` (its pros and cons are return-based)
   - `nav`, `nav_date`
   - `peerComparison`
   - `groww_rating`
6. **`m.historic_exit_loads`** holds older exit-load regimes. Ignore it and use only the current `m.exit_load`.

## Current values snapshot (2026-09-27)

| Scheme | Expense ratio | Exit load | Min SIP | Lock-in | Risk | Benchmark |
|---|---|---|---|---|---|---|
| Large Cap | 1.03% | 1% if redeemed within 1 year | ₹100 | None | Very High | NIFTY 100 TRI |
| Flexi Cap | 0.77% | 1% if redeemed within 1 year | ₹100 | None | Very High | NIFTY 500 TRI |
| ELSS Tax Saver | 1.21% | Nil | ₹500 | 3 years | Very High | NIFTY 500 TRI |
| Small Cap | 0.78% | 1% if redeemed within 1 year | ₹100 | None | Very High | BSE 250 SmallCap TRI |
| Balanced Advantage | 0.78% | 1% within 1 year on units above 15% of the investment | ₹100 | None | Very High | NIFTY 50 Hybrid Composite Debt 50:50 Index |
