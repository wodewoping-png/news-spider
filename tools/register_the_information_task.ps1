param(
    [string]$DailyAt = "07:15",
    [string]$TaskName = "NewsSpider-TheInformation"
)

$ErrorActionPreference = "Stop"
if ($DailyAt -notmatch "^(?:[01]\d|2[0-3]):[0-5]\d$") {
    throw "DailyAt must use 24-hour HH:mm format."
}
$publisher = (Resolve-Path (Join-Path $PSScriptRoot "publish_local_the_information.ps1")).Path
$action = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$publisher`""
& schtasks.exe /Create /F /SC DAILY /ST $DailyAt /TN $TaskName /TR $action
if ($LASTEXITCODE -ne 0) {
    throw "Unable to register Windows scheduled task $TaskName."
}
Write-Host "Registered $TaskName to run every day at $DailyAt local time."
