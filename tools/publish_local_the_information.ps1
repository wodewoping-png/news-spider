param(
    [string]$TargetDate = "",
    [string]$InboxBranch = "the-information-inbox",
    [string]$Remote = "origin",
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $TargetDate) {
    $chinaTimeZone = [TimeZoneInfo]::FindSystemTimeZoneById("China Standard Time")
    $chinaNow = [TimeZoneInfo]::ConvertTime([DateTimeOffset]::UtcNow, $chinaTimeZone)
    $TargetDate = $chinaNow.Date.AddDays(-1).ToString("yyyy-MM-dd")
}
try {
    [void][datetime]::ParseExact(
        $TargetDate,
        "yyyy-MM-dd",
        [Globalization.CultureInfo]::InvariantCulture
    )
} catch {
    throw "TargetDate must use YYYY-MM-DD: $TargetDate"
}
$captureRoot = Join-Path ([IO.Path]::GetTempPath()) (
    "news-spider-the-information-" + [guid]::NewGuid().ToString("N")
)
$resolvedTempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$resolvedCaptureRoot = [IO.Path]::GetFullPath($captureRoot)
if (-not $resolvedCaptureRoot.StartsWith($resolvedTempRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to use a capture directory outside the system temporary directory."
}
$captureData = Join-Path $captureRoot "capture.jsonl"
$captureCsv = Join-Path $captureRoot "capture.csv"
$captureLogs = Join-Path $captureRoot "logs"
$packageDir = Join-Path $captureRoot "package"
$worktreePath = Join-Path $captureRoot "inbox-worktree"

New-Item -ItemType Directory -Path $captureRoot | Out-Null
try {
    Push-Location $projectRoot
    try {
        & $Python -m src.main `
            --sources sources.xlsx `
            --only-source "the information" `
            --target-date $TargetDate `
            --output $captureData `
            --csv $captureCsv `
            --logs $captureLogs `
            --the-information-public-only `
            --skip-industry-classification `
            --skip-audit
        if ($LASTEXITCODE -ne 0) {
            throw "The Information local crawler exited with code $LASTEXITCODE."
        }

        & $Python -m src.local_the_information package `
            --articles $captureData `
            --health (Join-Path $captureLogs "channel-health.json") `
            --output-dir $packageDir `
            --target-date $TargetDate
        if ($LASTEXITCODE -ne 0) {
            throw "The Information capture did not pass public-feed validation."
        }

        & git fetch $Remote main
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to fetch $Remote/main."
        }
        & git ls-remote --exit-code --heads $Remote "refs/heads/$InboxBranch" *> $null
        $inboxExists = $LASTEXITCODE -eq 0
        if ($inboxExists) {
            & git fetch $Remote "$InboxBranch`:refs/remotes/$Remote/$InboxBranch"
            if ($LASTEXITCODE -ne 0) {
                throw "Unable to fetch $Remote/$InboxBranch."
            }
            & git worktree add --detach $worktreePath "$Remote/$InboxBranch"
        } else {
            & git worktree add --detach $worktreePath "$Remote/main"
        }
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to create the temporary inbox worktree."
        }

        $destination = Join-Path $worktreePath "incoming\the-information"
        New-Item -ItemType Directory -Path $destination -Force | Out-Null
        Copy-Item -LiteralPath (Join-Path $packageDir "$TargetDate.jsonl") -Destination $destination
        Copy-Item -LiteralPath (Join-Path $packageDir "$TargetDate.manifest.json") -Destination $destination
        & git -C $worktreePath add -- "incoming/the-information/$TargetDate.jsonl" "incoming/the-information/$TargetDate.manifest.json"
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to stage the local capture."
        }
        & git -C $worktreePath diff --cached --quiet
        if ($LASTEXITCODE -eq 0) {
            Write-Host "The Information $TargetDate capture is already published."
            return
        }
        & git -C $worktreePath -c user.name="news-spider-local" -c user.email="news-spider-local@users.noreply.github.com" commit -m "inbox: The Information $TargetDate"
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to commit the local capture."
        }
        # The temporary worktree is detached, so Git cannot infer that a new
        # remote destination is a branch. Use a fully qualified refspec for
        # both the first publish and subsequent updates.
        & git -C $worktreePath push $Remote "HEAD:refs/heads/$InboxBranch"
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to push the local capture to $InboxBranch."
        }
        Write-Host "Published public The Information RSS capture for $TargetDate."
    } finally {
        Pop-Location
    }
} finally {
    if (Test-Path -LiteralPath $worktreePath) {
        & git -C $projectRoot worktree remove --force $worktreePath 2>$null
    }
    if (Test-Path -LiteralPath $captureRoot) {
        Remove-Item -LiteralPath $captureRoot -Recurse -Force
    }
}
