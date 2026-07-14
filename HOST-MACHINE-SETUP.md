# Host Machine Setup: Keeping the Presto Sync Alive

This box runs the WCL/Presto live stats sync via Task Scheduler. The sync drives
**real, headed Chrome** (Playwright `channel="chrome"`, non-headless) because Presto
serves a Human Verification wall to datacenter IPs and headless browsers. That means
the machine must stay (a) awake and (b) logged in to an interactive session, or the
visible Chrome window has nowhere to render and the sync fails silently.

These settings were applied 2026-06-16 to stop the machine going dark after Windows
Updates and other events.

## What's running
- **WCL live refresh** — Task Scheduler: 10:00 AM daily, repeats every 5 min for ~16 hrs.
  This is the one that matters. Covers ~10 AM to 2 AM.
- **WCL 3:00 AM daily job** — non-essential; safe to leave or disable.

## Settings applied

### 1. Never sleep on AC power
```powershell
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /change monitor-timeout-ac 0   # optional; display can still sleep
```
Verify: `powercfg /q SCHEME_CURRENT SUB_SLEEP STANDBYIDLE` → Current AC Power Setting
Index should be `0x00000000`. (DC/battery value is left at default and doesn't matter
for a plugged-in box.)

### 2. Block forced reboots while logged on (primary reboot fix)
```powershell
New-Item -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU" -Force | Out-Null
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU" -Name "NoAutoRebootWithLoggedOnUsers" -Value 1 -Type DWord
```
Verify: `Get-ItemProperty ... -Name "NoAutoRebootWithLoggedOnUsers"` → `1`.

Windows still downloads and installs updates; it just won't auto-restart while a user
is logged on. Chosen over native Active Hours because the live task runs nearly all
day and Active Hours caps at an 18-hour window.

**Tradeoff:** updates needing a reboot sit in "pending restart" until a manual reboot.
Mitigated by logging in remotely ~once a day and rebooting when convenient so patches
don't stack up. Reversible: set value to `0` or delete the key.

### 3. Auto sign-in after reboot (safety net — optional, do via UI)
Settings → Accounts → Sign-in options → "Use my sign-in info to automatically finish
setting up after an update and reopen my apps" → **On**. Restores the interactive
session after any hard reboot (power flicker, manual restart) so headed Chrome has a
desktop again.

## Task Scheduler settings to confirm on the live task
- General: "Run only when user is logged on" (NOT "whether logged on or not" — headed
  Chrome can't render in session 0).
- Conditions: "Wake the computer to run this task" checked.
- Settings: "Run task as soon as possible after a scheduled start is missed" checked;
  optional retry every 10 min, up to 3 times.

## If the sync stops
1. Is the machine awake and **logged in**? (Lock screen = headed Chrome can't draw.)
2. Pending reboot from updates? Reboot, confirm auto sign-in brought the session back.
3. Run refresh.ps1 manually to check Chrome launches a visible window.
4. WCL_HEADLESS must NOT be set to 1 (headless trips the Presto bot wall).
