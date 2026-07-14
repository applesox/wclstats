# WCL 2026 Standings: First Half / Second Half / Overall

**File:** `wcl-standings-halves.html` (self-contained, no external dependencies)
**Built:** 2026-07-08. **Data as of:** first half FINAL; second half through 7/5/2026.
**Intended host:** westcoastleague.com (embed)
**Style reference:** matches the existing wclstats page (`./index.html`): navy `#243746` headers, teal `#1a769f` accents, tabs, division filter pills, AppleSox row highlight.

## What it is
A single embeddable page with three tabs.

**First Half** is locked/final. Each club's first-half W-L comes from the WCL playoff-picture spreadsheet (`1H W` / `1H L` columns) and never changes. The division first-half champion (Wenatchee AppleSox in the North, Ridgefield Raptors in the South) is flagged with a green "1H CHAMP · BERTH" badge and a star, meaning they have clinched a playoff berth.

**Second Half** is in progress. It is computed as `Overall minus First Half`, so it never needs to be edited directly; it stays in sync whenever the overall totals are refreshed.

**Overall** is intentionally a link out to the official Presto standings (`https://wclstats.com/sports/bsb/2026/standings`) rather than a duplicated table, since Presto carries the live tiebreakers, streaks, and last-10.

The table is a flat sortable grid (click any header) with All-16 / North / South filter pills. GB is computed within each division (games behind that division's leader), because the first- and second-half titles are decided by division.

## How to update going forward
Only one thing ever changes: the `[overallW, overallL]` pair for each team in the `DATA` array near the top of the file. First-half numbers are final and frozen; the second half re-derives itself. Also bump the `ASOF` string above `DATA`.

`DATA` row format: `[ team, division(N/S), firstHalfW, firstHalfL, overallW, overallL ]`

If we ever want the overall numbers to auto-refresh, they can be fed by the same local-Chrome Presto pull the wclstats page already uses. (Presto bot-walls datacenter IPs, so a refresh must run on a residential machine. See the wclstats HOST-MACHINE-SETUP notes.)

## Data snapshot baked in (as of 7/5/2026)
Source spreadsheet: "WCL 2026 Playoffs Picture Sorted by 2H Standings.xlsx".
Verified: `Overall minus First Half = Second Half` for all 16 teams (0 mismatches vs the spreadsheet's own 2H column).

| Team | Div | 1H (final) | Overall | 2H (derived) |
|---|---|---|---|---|
| Wenatchee AppleSox | N | 19-8 | 22-9 | 3-1 |
| Kelowna Falcons | N | 16-11 | 20-11 | 4-0 |
| Bellingham Bells | N | 19-8 | 20-13 | 1-5 |
| Nanaimo NightOwls | N | 15-12 | 19-15 | 4-3 |
| Edmonton Riverhawks | N | 14-12 | 15-15 | 1-3 |
| Victoria HarbourCats | N | 14-13 | 15-16 | 1-3 |
| Kamloops NorthPaws | N | 11-16 | 12-19 | 1-3 |
| Port Angeles Lefties | N | 5-21 | 7-23 | 2-2 |
| Ridgefield Raptors | S | 20-7 | 20-11 | 0-4 |
| Walla Walla Sweets | S | 15-12 | 20-14 | 5-2 |
| Corvallis Knights | S | 13-14 | 17-14 | 4-0 |
| Yakima Valley Pippins | S | 12-15 | 15-16 | 3-1 |
| Portland Pickles | S | 11-13 | 13-15 | 2-2 |
| Bend Elks | S | 11-14 | 12-17 | 1-3 |
| Marion Berries | S | 12-14 | 13-19 | 1-5 |
| Springfield Drifters | S | 9-18 | 9-22 | 0-4 |

## Open items / review
Sent to Rob Neyer (WCL Commissioner, rneyer@gmail.com) for review on 2026-07-08. Sent as a PDF (`WCL_Standings_Preview.pdf`) because HTML attachments open as raw source in Outlook.

Two questions pending Rob's confirmation:
1. The North first-half title was a 19-8 tie between Wenatchee and Bellingham. The page shows Wenatchee as first-half champ, per the spreadsheet's "Clinched #1 Seed in North" note. Confirm the official tiebreaker.
2. The playoff-berth framing ("first-half and second-half division champions clinch berths") reads right for fans.

After sign-off: embed on westcoastleague.com (manual WinSCP deploy to DreamHost, per the WCL deploy mechanism).

## Playoff context
WCL awards a playoff berth to each division's first-half champion and each division's second-half champion. If one club wins both halves in its division, the second berth typically goes to the next-best club by overall record. Presto and league procedures govern the exact tiebreak (`https://westcoastleague.com/playoff-procedures/`).
