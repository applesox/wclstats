# Presto Relay (soxlive standby) - setup

No em-dashes per preference.

## What this is / why
Presto's Cloudflare bot-walls DreamHost's server (every composite fetch returns HTTP 202, empty), so the site cannot pull the day-pages itself. This relay runs on a RESIDENTIAL machine (soxlive), fetches the composite day-pages with real Chrome (not walled), and SFTPs them plus a manifest to DreamHost. The theme's `composite_page` source (already enabled via the WCL_PRESTO_CAROUSEL_SOURCE define) reads that mirror locally and renders finals + live innings.

Files: presto-relay.py, relay-config.example.json. Output on the server: wp-content/uploads/presto-relay/manifest.json + one <date>.html per day.

## Prerequisites (soxlive already has most of this from the wclstats setup)
- Python 3.12, Playwright, and real Chrome (already installed for generate.py).
- One extra library:  `pip install paramiko`
- If Playwright's browser is missing:  `python -m playwright install chromium`  (real Chrome via channel="chrome" is used first).

## One-time DreamHost setup (you do this - I cannot handle credentials)
1. In the DreamHost panel, get or create an SFTP/Shell user for westcoastleague.com (Users -> Manage Users), or ask Paul. Note the SFTP host (e.g. iad1-shared-xxxx.dreamhost.com) and the username.
2. Set up key-based auth (recommended, no password on disk):
   - On soxlive:  `ssh-keygen -t ed25519 -f %USERPROFILE%\.ssh\dreamhost_ed25519`
   - Add the .pub key to that DreamHost user (panel -> the user -> add SSH key, or append to ~/.ssh/authorized_keys on the server).
3. Find the target path: on DreamHost shared hosting the site lives at /home/<user>/westcoastleague.com/ , so the folder is:
   /home/<user>/westcoastleague.com/wp-content/uploads/presto-relay
   (The script creates the presto-relay folder if it does not exist.)

## Configure
Copy relay-config.example.json to relay-config.json (same folder as the script) and fill in sftp_host, sftp_user, sftp_key_path, and remote_dir. Leave sftp_key_passphrase empty unless your key has one. days_back/days_forward default to 2/2 (yesterday-2 .. today+2), which covers recent finals, today's live games, and the next couple of days.
Do NOT commit relay-config.json or your private key anywhere. If you must use a password instead of a key, set it in the environment as WCL_RELAY_SFTP_PASSWORD (never in the file).

## Test
    cd ~\wclstats   (or wherever you put the relay)
    python presto-relay.py
Watch presto-relay.log. On success it logs "uploaded N day-page(s) + manifest ...". Then hard-refresh westcoastleague.com: completed games should show finals (F + score) and any in-progress game should show a live score + inning. It can take a minute for the theme's per-day cache to pick up the mirror.

## Schedule (this is what makes it a real relay)
The theme ignores the manifest once it is older than 15 minutes, so run this on a short interval during game hours. Task Scheduler:
- Program:  python  (or full path to python.exe)
- Arguments:  <path>\presto-relay.py
- Trigger: every 3-5 minutes (at least every 15). Daily is fine; games are evenings.
- Name it "WCL Presto Relay (soxlive)". Enable "Run task as soon as possible after a scheduled start is missed."
This is separate from "WCL Stats Backup (soxlive)" (that one pushes the standings page).

## Fail-safe behavior (already built in)
- If a fetch is challenged / a day has no games, that date is skipped (never mirrors a junk page - the theme requires "event-row").
- If NOTHING fetches, the script uploads nothing and exits non-zero, leaving the last good mirror in place. When the mirror ages past 15 min the ribbon simply falls back to the schedule feed (no scores) until the next good run - it never shows garbage.
- Day files are uploaded before the manifest, so a reader never sees a manifest pointing at a file that has not landed.

## Coordination + housekeeping
- When newstudio returns: only ONE machine needs to run the relay. Running both is harmless (last write wins) but wasteful; pick one, or keep soxlive as the standby and let newstudio be primary.
- Old <date>.html files accumulate in presto-relay/ as the window moves. They are harmless (the manifest only references current dates); clear them out occasionally if you like.
- Remove the temporary diagnostic block (?wcl_cp_diag) from functions.php now that we are done with it.
