# Local daily refresh (runs on your PC, not GitHub)

wclstats.com (Presto) blocks datacenter IPs with a "Human Verification" wall, so
the scrape can't run on GitHub's servers. Instead it runs here, on your PC's normal
network, using your real Chrome — then pushes the result, and GitHub Pages serves it.

## One-time prerequisites

1. Install the Playwright Python package (Chrome itself you already have):
   ```
   pip install playwright
   ```
   (No `playwright install` needed — `generate.py` uses your installed Chrome via
   `channel="chrome"`.)

2. Confirm git can push without prompting (it can — `gh auth login` set that up).

## Test it manually first

```
powershell -ExecutionPolicy Bypass -File C:\ClaudeRoot\AppleSoxWCL\wclstats\refresh.ps1
```

A Chrome window will open briefly, load the wclstats pages, then close. Expected output:
`[refresh] pushed update ...` (or `no change to publish`). Then check
**https://applesox.github.io/wclstats/**.

If you instead see it fail with a `Human Verification` diag line, Presto is challenging
even this machine — tell Claude and we'll switch to running it through your existing
Presto residential relay.

## Schedule it (~3 AM daily)

Run this once in an **Administrator** PowerShell to register the task:

```
schtasks /Create /TN "WCL Stats Daily" ^
  /TR "powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File C:\ClaudeRoot\AppleSoxWCL\wclstats\refresh.ps1" ^
  /SC DAILY /ST 03:00 /F
```

Notes:
- The PC must be awake at 3 AM for it to run (Task Scheduler can wake it: Task Scheduler
  app → WCL Stats Daily → Properties → Conditions → "Wake the computer to run this task").
- Run on demand anytime: `schtasks /Run /TN "WCL Stats Daily"`.
- Remove it: `schtasks /Delete /TN "WCL Stats Daily" /F`.

## What changed vs. the GitHub Action

- `.github/workflows/wclstats.yml` is now manual-only (no nightly cron), so it stops
  failing every night. It stays runnable from the Actions tab in case Presto ever stops
  blocking datacenter IPs.
- The daily commit now comes from this machine instead of `github-actions[bot]`.
