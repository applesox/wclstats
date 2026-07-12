$ErrorActionPreference = "Stop"
$RepoDir = "$HOME\wclstats"
$Log = "$RepoDir\backup-runner.log"
Set-Location $RepoDir

git fetch origin main --quiet
$last = [int](git log -1 --format=%ct origin/main)
$ageHours = ([DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - $last) / 3600
"{0:u}  origin/main is {1:N1}h old" -f (Get-Date), $ageHours | Tee-Object $Log -Append

if ($ageHours -lt 20) {
    "Primary already refreshed - standby skipping." | Tee-Object $Log -Append
    exit 0
}

"Primary missed its run - executing backup refresh." | Tee-Object $Log -Append
git pull --rebase origin main --quiet

# Scrape Presto and regenerate index.html (exits non-zero on failure,
# so a bad scrape never overwrites a good page)
python "$RepoDir\generate.py"
if ($LASTEXITCODE -ne 0) {
    "generate.py FAILED (exit $LASTEXITCODE) - aborting, page left unchanged." | Tee-Object $Log -Append
    exit 1
}

git add index.html
git commit -m "Auto-refresh standings (backup runner: soxlive)" 2>&1 | Tee-Object $Log -Append
git push origin main 2>&1 | Tee-Object $Log -Append
"Backup refresh pushed successfully." | Tee-Object $Log -Append
