#!/usr/bin/env python3
"""
Standby Presto relay for the westcoastleague.com scoreboard ribbon.

Runs on a RESIDENTIAL machine (soxlive). Presto's Cloudflare bot-walls DreamHost's
datacenter IP (every server fetch returns HTTP 202 / empty), so the WordPress theme
cannot pull the composite day-pages itself. This relay fetches those pages with a real
browser from a residential IP (not walled) and SFTPs them, plus a manifest, to
DreamHost. The theme's `composite_page` source then reads them locally and renders
finals + live innings.

FORMAT IS DICTATED BY THE THEME (wcl-presto.php). Do not change it without checking
wcl_presto_relay_manifest() / wcl_presto_relay_read_day():
  <remote_dir>/manifest.json = {"generated_at_epoch": <int unix>, "files": {"YYYY-MM-DD": "<file>"}}
  <remote_dir>/<file>        = raw rendered HTML of https://wclstats.com/composite?d=YYYY-MM-DD
                               (MUST contain the string "event-row" or the theme rejects it)
The theme IGNORES the manifest if generated_at_epoch is older than 15 minutes, so this
must run at least every ~15 min during the day (Task Scheduler; every 3-5 min is ideal).

SETUP: see RELAY_SETUP.md. Create relay-config.json (copy relay-config.example.json) with
your DreamHost SFTP details. Prefer an SSH key; never put a password in the config file.

Requires: playwright (+ chromium/real Chrome) and paramiko. Both are pip-installable.
"""
import os
import sys
import json
import time
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("America/Los_Angeles")
except Exception:
    TZ = None

from playwright.sync_api import sync_playwright
import paramiko

HERE        = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "relay-config.json")
WORK_DIR    = os.path.join(HERE, "relay-work")
LOG_PATH    = os.path.join(HERE, "presto-relay.log")
COMPOSITE   = "https://wclstats.com/composite?d={date}"


def log(msg):
    ts = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S %Z") if TZ else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = "{}  {}".format(ts, msg)
    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_config():
    if not os.path.exists(CONFIG_PATH):
        log("ERROR: config not found: {} (copy relay-config.example.json and fill it in)".format(CONFIG_PATH))
        sys.exit(1)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    missing = [k for k in ("sftp_host", "sftp_user", "remote_dir") if not cfg.get(k)]
    if missing:
        log("ERROR: relay-config.json missing keys: {}".format(missing))
        sys.exit(1)
    cfg.setdefault("sftp_port", 22)
    cfg.setdefault("days_back", 2)
    cfg.setdefault("days_forward", 2)
    return cfg


def date_window(days_back, days_forward):
    today = (datetime.now(TZ) if TZ else datetime.now()).date()
    return [(today + timedelta(days=d)).isoformat() for d in range(-int(days_back), int(days_forward) + 1)]


def fetch_days(dates):
    """Return {date: html} for each date whose composite page rendered with event-row."""
    out = {}
    headless = os.environ.get("WCL_HEADLESS", "0") == "1"
    with sync_playwright() as p:
        # Presto serves a human-verification wall to datacenter/headless clients. Run on a
        # residential machine with real Chrome. Headful is most reliable past Cloudflare;
        # set WCL_HEADLESS=1 only for debugging.
        try:
            browser = p.chromium.launch(channel="chrome", headless=headless)
        except Exception:
            browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        for d in dates:
            url = COMPOSITE.format(date=d)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                try:
                    page.wait_for_selector(".event-row", timeout=20000)
                except Exception:
                    page.wait_for_timeout(4000)
                html = page.content()
            except Exception as e:
                log("  d={}: fetch error: {}".format(d, e))
                continue
            if "event-row" not in html:
                # A challenge page or an empty/off day: skip so we never mirror junk.
                log("  d={}: no 'event-row' (skipped, len={})".format(d, len(html)))
                continue
            out[d] = html
            log("  d={}: ok (len={})".format(d, len(html)))
        browser.close()
    return out


def write_local(day_html):
    os.makedirs(WORK_DIR, exist_ok=True)
    files = {}
    for d, html in day_html.items():
        fname = "{}.html".format(d)
        with open(os.path.join(WORK_DIR, fname), "w", encoding="utf-8") as f:
            f.write(html)
        files[d] = fname
    manifest = {"generated_at_epoch": int(time.time()), "files": files}
    with open(os.path.join(WORK_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f)
    return files


def load_key(path, passphrase):
    for cls in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey):
        try:
            return cls.from_private_key_file(path, password=passphrase or None)
        except Exception:
            continue
    raise RuntimeError("could not load private key: {}".format(path))


def ensure_remote_dir(sftp, remote_dir):
    cur = ""
    for part in remote_dir.strip("/").split("/"):
        cur += "/" + part
        try:
            sftp.stat(cur)
        except IOError:
            sftp.mkdir(cur)


def upload(cfg, files):
    transport = paramiko.Transport((cfg["sftp_host"], int(cfg["sftp_port"])))
    pkey = load_key(cfg["sftp_key_path"], cfg.get("sftp_key_passphrase")) if cfg.get("sftp_key_path") else None
    # Password, if used at all, comes only from an env var so it is never written to disk.
    password = os.environ.get("WCL_RELAY_SFTP_PASSWORD")
    transport.connect(username=cfg["sftp_user"], pkey=pkey, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    try:
        remote = cfg["remote_dir"].rstrip("/")
        ensure_remote_dir(sftp, remote)
        # Upload day files first, then the manifest LAST, so a reader never sees a manifest
        # that references a file which has not finished landing.
        for d, fname in files.items():
            sftp.put(os.path.join(WORK_DIR, fname), remote + "/" + fname)
        sftp.put(os.path.join(WORK_DIR, "manifest.json"), remote + "/manifest.json")
    finally:
        sftp.close()
        transport.close()


def main():
    cfg = load_config()
    dates = date_window(cfg["days_back"], cfg["days_forward"])
    log("relay run: {}..{}".format(dates[0], dates[-1]))
    day_html = fetch_days(dates)
    # Fail-closed: never write an empty/partial manifest. If nothing fetched, leave the last
    # good mirror in place (it will simply age out after 15 min and the ribbon falls back to
    # the schedule feed until the next successful run).
    if not day_html:
        log("ERROR: 0 day-pages fetched - NOT uploading (preserving last-good mirror).")
        sys.exit(1)
    files = write_local(day_html)
    upload(cfg, files)
    log("uploaded {} day-page(s) + manifest to {}".format(len(files), cfg["remote_dir"]))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        log("ERROR: {}".format(e))
        sys.exit(1)
