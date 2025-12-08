# Automatic Backup Scheduler for Windows
# This script creates a Windows Task Scheduler task that runs daily at 00:00 (midnight) Asia/Manila time
#
# USAGE:
#   Run this script once as Administrator to set up the automatic backup:
#   powershell -ExecutionPolicy Bypass -File setup_backup_scheduler.ps1

$taskName = "ISSC_AutoBackup"
$scriptPath = $PSScriptRoot
$pythonPath = Join-Path $scriptPath "venv\Scripts\python.exe"
$managePath = Join-Path $scriptPath "issc\manage.py"

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "ISSC Automatic Backup Scheduler Setup (Windows)" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Please right-click PowerShell and select 'Run as Administrator', then run this script again." -ForegroundColor Yellow
    pause
    exit 1
}

# Verify files exist
if (-not (Test-Path $pythonPath)) {
    Write-Host "ERROR: Python executable not found at: $pythonPath" -ForegroundColor Red
    Write-Host "Please ensure your virtual environment is set up correctly." -ForegroundColor Yellow
    pause
    exit 1
}

if (-not (Test-Path $managePath)) {
    Write-Host "ERROR: manage.py not found at: $managePath" -ForegroundColor Red
    pause
    exit 1
}

Write-Host "Found Python: $pythonPath" -ForegroundColor Green
Write-Host "Found manage.py: $managePath" -ForegroundColor Green
Write-Host ""

# Remove existing task if it exists
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing scheduled task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Create the scheduled task
Write-Host "Creating scheduled task: $taskName" -ForegroundColor Cyan

# Task action - run the Django management command
$action = New-ScheduledTaskAction -Execute $pythonPath `
    -Argument "`"$managePath`" auto_backup --cleanup --keep-days 30" `
    -WorkingDirectory (Join-Path $scriptPath "issc")

# Task trigger - daily at 00:00
# Note: Windows Task Scheduler uses local time. Adjust if your system time is not Asia/Manila
$trigger = New-ScheduledTaskTrigger -Daily -At "00:00"

# Task settings
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# Task principal (run as current user)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest

# Register the task
Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Automatic database backup for ISSC system (runs daily at 00:00)"

Write-Host ""
Write-Host "===============================================" -ForegroundColor Green
Write-Host "✓ Automatic backup scheduler installed!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Task Details:" -ForegroundColor Cyan
Write-Host "  Name: $taskName" -ForegroundColor White
Write-Host "  Schedule: Daily at 00:00 (midnight)" -ForegroundColor White
Write-Host "  Cleanup: Automatic backups older than 30 days will be deleted" -ForegroundColor White
Write-Host ""
Write-Host "To verify the task was created, run:" -ForegroundColor Yellow
Write-Host "  Get-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
Write-Host ""
Write-Host "To manually run the backup now, run:" -ForegroundColor Yellow
Write-Host "  cd issc" -ForegroundColor White
Write-Host "  python manage.py auto_backup" -ForegroundColor White
Write-Host ""
Write-Host "To remove the scheduled task, run:" -ForegroundColor Yellow
Write-Host "  Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false" -ForegroundColor White
Write-Host ""
Write-Host "IMPORTANT: Make sure your system time is set to Asia/Manila timezone!" -ForegroundColor Yellow
Write-Host "You can verify this by running: Get-TimeZone" -ForegroundColor White
Write-Host ""

pause
