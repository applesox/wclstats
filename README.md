# WCL Stats — auto-updating standings & expected wins

A self-contained page for all 16 West Coast League teams (standings, offense,
pitching & defense, plus Pythagorean expected wins). A GitHub Action rebuilds it
daily (~3 AM Pacific) from wclstats.com, so the published URL is always current and
every update is a commit. It runs on GitHub's servers — nothing needs to be open on
any machine.

Published at: **https://applesox.github.io/wclstats/**  *(or jose-applesox.github.io/wclstats/ if you create it under your personal account)*

## Files
```
index.html        the page (overwritten daily by the Action)
template.html     layout the generator fills — edit this to restyle
generate.py       scrapes wclstats.com (headless Chromium) and rewrites index.html
requirements.txt
.github/workflows/wclstats.yml   daily schedule + build steps
```

## First-time setup

1. **Create an empty repo on GitHub** named `wclstats` (Owner: the `applesox`
   org for branding, or `jose-applesox`). Do NOT add a README/.gitignore/license —
   keep it empty so the first push is clean. Public.

2. **Push this folder** (run in `C:\ClaudeRoot\AppleSoxWCL\wclstats`):
   ```
   git init
   git branch -M main
   git add .
   git commit -m "WCL stats page + daily updater"
   git remote add origin https://github.com/applesox/wclstats.git
   git push -u origin main
   ```
   (Swap `applesox` for `jose-applesox` in the remote URL if you made it there.)

3. **Enable Pages:** repo → Settings → Pages → Source: *Deploy from a branch* →
   Branch: `main` / `/ (root)` → Save.

4. **Let the Action commit:** repo → Settings → Actions → General → Workflow
   permissions → **Read and write permissions** → Save.

5. **Test now:** repo → Actions → "Update WCL Stats Page" → **Run workflow**.

## Notes
- Two cron lines (10:00 / 11:00 UTC) keep it near 3 AM Pacific across DST. Trim to one if you like.
- `generate.py` exits non-zero (page left unchanged) if it can't read the stat tables, so a bad scrape never publishes garbage.
- If a column comes through wrong after a wclstats layout change, the fix is in the `col(...)` header lookups in `generate.py`.
- Divisions are hard-coded (NORTH / SOUTH sets in `generate.py`); update if membership changes.
