<#
  refresh.ps1 — regenerate the WCL stats page and push it to GitHub Pages.

  Runs generate.py (which scrapes wclstats.com with your real Chrome) and, if
  index.html changed, commits and pushes. GitHub Pages then serves the update.

  Run manually to test:
    powershell -ExecutionPolicy Bypass -File C:\ClaudeRoot\AppleSoxWCL\wclstats\refresh.ps1

  Scheduled via Windows Task Scheduler (see SETUP-local.md).
#>

$ErrorActionPreference = "Stop"
$repo = "C:\ClaudeRoot\AppleSoxWCL\wclstats"
Set-Location $repo

# Use the same Python that's on PATH (your conda 'base' has it).
Write-Host "[refresh] regenerating index.html ..." -ForegroundColor Cyan
python generate.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[refresh] generate.py failed (exit $LASTEXITCODE) - not pushing." -ForegroundColor Yellow
    exit $LASTEXITCODE
}

# Push if index.html (or the WCL logo asset) changed.
git add index.html wcl-logo.png
git diff --staged --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "[refresh] no change to publish." -ForegroundColor Green
} else {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
    git commit -m "Update WCL stats $stamp"
    git push
    Write-Host "[refresh] pushed update ($stamp)." -ForegroundColor Green
}
