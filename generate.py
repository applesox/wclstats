#!/usr/bin/env python3
"""
Regenerate stats/index.html for the WCL standings & expected-wins page.

Scrapes the JavaScript-rendered Presto stat pages on wclstats.com with a headless
browser, then renders the data into template.html. Designed to run in GitHub Actions
(see .github/workflows/wcl-stats.yml) but also runs locally if Playwright + Chromium
are installed:  pip install -r requirements.txt && python -m playwright install chromium

Output: writes index.html next to this file. Exits non-zero on scrape failure so a
bad run doesn't overwrite a good page with garbage.
"""
import json, os, sys
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None
from playwright.sync_api import sync_playwright

YEAR = 2026
BASE = f"https://wclstats.com/sports/bsb/{YEAR}"
HERE = os.path.dirname(os.path.abspath(__file__))

# Divisions are fixed for the season -> assign locally, don't rely on page order.
NORTH = {"Bellingham Bells","Edmonton Riverhawks","Kamloops NorthPaws","Kelowna Falcons",
         "Nanaimo NightOwls","Port Angeles Lefties","Victoria HarbourCats","Wenatchee AppleSox"}
SOUTH = {"Bend Elks","Corvallis Knights","Marion Berries","Portland Pickles","Ridgefield Raptors",
         "Springfield Drifters","Walla Walla Sweets","Yakima Valley Pippins"}
ALL_TEAMS = NORTH | SOUTH

# JS that pulls the currently-VISIBLE team table as {heads, rows}.
# The Presto team-stats page keeps all 5 category tables (Hitting, Base Running,
# Pitching, Fielding, Attendance) in the DOM and shows one at a time; hidden tables
# return empty innerText, so we must select the visible one, preferring a 'TEAM' header.
EXTRACT = """() => {
  const isVisible = el => {
    if(!el) return false;
    const s = getComputedStyle(el);
    if(s.display==='none' || s.visibility==='hidden') return false;
    return el.offsetParent !== null || s.position==='fixed';
  };
  const tables=[...document.querySelectorAll('table')].filter(isVisible);
  let best=null,score=-1;
  for(const t of tables){
    const heads=[...t.querySelectorAll('thead th')].map(th=>th.innerText.trim().toUpperCase());
    const rows=t.querySelectorAll('tbody tr').length;
    const s = rows + (heads.includes('TEAM') ? 1000 : 0);
    if(s>score){score=s;best=t;}
  }
  if(!best) return null;
  const hrow = best.querySelector('thead tr');
  const heads = hrow ? [...hrow.querySelectorAll('th')].map(th=>th.innerText.trim()) : [];
  const rows = [...best.querySelectorAll('tbody tr')]
      .map(tr=>[...tr.querySelectorAll('td')].map(td=>td.innerText.trim()))
      .filter(r=>r.some(c=>c));
  return {heads, rows};
}"""

def num(x):
    x = (x or "").strip().replace(",", "")
    if x in ("", "-", "--"): return 0
    try:
        return float(x) if "." in x else int(x)
    except ValueError:
        return 0

def clean_team(name):
    return " ".join((name or "").split())

def col(heads, *names):
    """Index of the first header matching any of names (case-insensitive, exact then prefix)."""
    low = [h.lower() for h in heads]
    for nm in names:
        nm = nm.lower()
        if nm in low: return low.index(nm)
    for nm in names:
        nm = nm.lower()
        for i, h in enumerate(low):
            if h.startswith(nm): return i
    return -1

def grab(page, url, category=None):
    page.goto(url, wait_until="networkidle", timeout=60000)
    if category:
        # pick the <select> whose options include the category label, then choose it
        for sel in page.query_selector_all("select"):
            opts = [o.inner_text().strip().lower() for o in sel.query_selector_all("option")]
            if category.lower() in opts:
                sel.select_option(label=category)
                page.wait_for_load_state("networkidle", timeout=60000)
                break
    # wait until the data table has the full team set rendered
    try:
        page.wait_for_function(
            "() => [...document.querySelectorAll('table tbody tr')].length >= 16",
            timeout=30000)
    except Exception:
        pass
    data = page.evaluate(EXTRACT)
    nrows = len(data["rows"]) if data else 0
    print(f"[diag] grab {category!r}: heads={data['heads'][:9] if data else None} "
          f"nrows={nrows} firstrow={data['rows'][0][:5] if (data and data['rows']) else None}",
          file=sys.stderr)
    if not data or not data["rows"]:
        snip = page.evaluate("() => (document.body ? document.body.innerText : '').slice(0,500)")
        raise RuntimeError(f"no table rows at {url} ({category}); title={page.title()!r}; body[:500]={snip!r}")
    return data

def rows_by_team(data, team_hint=("team",)):
    heads, rows = data["heads"], data["rows"]
    ti = col(heads, *team_hint)
    if ti < 0: ti = 1 if len(rows[0]) > 1 else 0
    out = {}
    for r in rows:
        if ti >= len(r): continue
        name = clean_team(r[ti])
        if name in ALL_TEAMS:
            out[name] = (heads, r)
    return out

def main():
    teams = {t: {} for t in ALL_TEAMS}

    with sync_playwright() as p:
        # Presto serves a "Human Verification" wall to datacenter IPs and headless
        # browsers. Run on a residential machine using real Chrome in a normal window.
        # Set WCL_HEADLESS=1 to force headless (e.g. for debugging).
        headless = os.environ.get("WCL_HEADLESS", "0") == "1"
        try:
            browser = p.chromium.launch(channel="chrome", headless=headless)
        except Exception:
            browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        # --- Standings: W, L ---
        page.goto(f"{BASE}/standings", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        rows_seen = page.evaluate("() => document.querySelectorAll('table tbody tr').length")
        print(f"[diag] standings: title={page.title()!r} url={page.url} tbody_rows={rows_seen}", file=sys.stderr)
        if rows_seen < 8:
            snip = page.evaluate("() => (document.body ? document.body.innerText : '').slice(0,500)")
            print(f"[diag] standings body[:500]={snip!r}", file=sys.stderr)
            try:
                page.wait_for_function(
                    "() => document.querySelectorAll('table tbody tr').length >= 8", timeout=25000)
                print("[diag] standings rows appeared after extra wait", file=sys.stderr)
            except Exception:
                print("[diag] standings rows NEVER reached 8 (likely blocked/challenged)", file=sys.stderr)
        # Standings tables may not use <thead>; fall back to the first row for headers,
        # and locate the team cell by scanning (don't assume column 0).
        stand_tables = page.evaluate("""() => {
          const out=[];
          for(const t of document.querySelectorAll('table')){
            let heads=[...t.querySelectorAll('thead th')].map(e=>e.innerText.trim());
            let body=[...t.querySelectorAll('tbody tr')];
            if(heads.length===0){
              const trs=[...t.querySelectorAll('tr')];
              if(trs.length){ heads=[...trs[0].children].map(e=>e.innerText.trim()); body=trs.slice(1); }
            }
            const rows=body.map(tr=>[...tr.children].map(c=>c.innerText.trim())).filter(r=>r.some(x=>x));
            out.push({heads, rows});
          }
          return out;
        }""")
        for tbl in stand_tables:
            heads, rows = tbl["heads"], tbl["rows"]
            wi, li = col(heads, "w"), col(heads, "l")
            if wi < 0 or li < 0: continue
            for r in rows:
                name = next((clean_team(c) for c in r if clean_team(c) in ALL_TEAMS), None)
                if name and wi < len(r) and li < len(r):
                    teams[name]["W"] = int(num(r[wi])); teams[name]["L"] = int(num(r[li]))
        print(f"[diag] standings parsed W for {sum('W' in v for v in teams.values())}/{len(teams)} teams; "
              f"table_heads={[t['heads'][:6] for t in stand_tables]}", file=sys.stderr)

        # --- Hitting: GP, AVG, OBP, SLG, oBB, oK ---
        for name,(h,r) in rows_by_team(grab(page, f"{BASE}/teams?r=0", "Hitting")).items():
            teams[name].update(
                GP=int(num(r[col(h,"gp")])), AVG=num(r[col(h,"avg")]),
                OBP=num(r[col(h,"obp")]), SLG=num(r[col(h,"slg")]),
                oBB=int(num(r[col(h,"bb")])), oK=int(num(r[col(h,"k","so")])))

        # --- Base running: R (runs scored), SB ---
        for name,(h,r) in rows_by_team(grab(page, f"{BASE}/teams?sort=r&r=0&pos=br", "Base Running")).items():
            teams[name].update(RS=int(num(r[col(h,"r")])), SB=int(num(r[col(h,"sb")])))

        # --- Pitching: ERA, R (runs allowed), pBB, pK, WHIP, IP ---
        for name,(h,r) in rows_by_team(grab(page, f"{BASE}/teams?sort=era&r=0&pos=p", "Pitching")).items():
            teams[name].update(
                ERA=num(r[col(h,"era")]), RA=int(num(r[col(h,"r")])),
                pBB=int(num(r[col(h,"bb")])), pK=int(num(r[col(h,"k","so")])),
                WHIP=num(r[col(h,"whip")]), IP=num(r[col(h,"ip")]))

        # --- Fielding: E, F% ---
        for name,(h,r) in rows_by_team(grab(page, f"{BASE}/teams?sort=fpct&r=0&pos=f", "Fielding")).items():
            teams[name].update(E=int(num(r[col(h,"e")])), Fpct=num(r[col(h,"f%","fpct","fld%")]))

        browser.close()

    # assemble rows matching the template's DATA shape:
    # [team, div, W, L, GP, AVG, OBP, SLG, RS, RA, oBB, oK, E, SB, ERA, IP, pBB, pK, WHIP, Fpct]
    def g(t, k, d=0): return teams[t].get(k, d)
    missing = [t for t in ALL_TEAMS if "W" not in teams[t] or "AVG" not in teams[t]]
    if len(missing) > len(ALL_TEAMS) // 2:
        raise RuntimeError(f"too many teams missing data: {missing}")

    data = []
    for t in sorted(ALL_TEAMS, key=lambda x: (0 if x in NORTH else 1, -g(x,"W"), g(x,"L"))):
        dv = "N" if t in NORTH else "S"
        data.append([t, dv, g(t,"W"), g(t,"L"), g(t,"GP"),
                     g(t,"AVG"), g(t,"OBP"), g(t,"SLG"), g(t,"RS"), g(t,"RA"),
                     g(t,"oBB"), g(t,"oK"), g(t,"E"), g(t,"SB"),
                     g(t,"ERA"), g(t,"IP"), g(t,"pBB"), g(t,"pK"), g(t,"WHIP"), g(t,"Fpct")])

    now = datetime.now(ZoneInfo("America/Los_Angeles")) if ZoneInfo else datetime.now()
    # Avoid %-d / %-I (Linux-only strftime); build no-leading-zero parts manually for Windows.
    hr12 = now.hour % 12 or 12
    ampm = "AM" if now.hour < 12 else "PM"
    tz = now.strftime("%Z") or "PT"
    asof = (f"Auto-updated {now.strftime('%b')} {now.day}, {now.year} "
            f"{hr12}:{now.minute:02d} {ampm} {tz} · source: wclstats.com (Presto)")

    tmpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    html = tmpl.replace("__DATA__", json.dumps(data)).replace("__ASOF__", asof)
    open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(html)
    print(f"wrote index.html with {len(data)} teams")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
