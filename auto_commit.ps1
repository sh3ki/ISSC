# Auto Commit Script - Commits files one at a time
# Pushes to master after all commits

$ErrorActionPreference = "Continue"
$workingDir = "C:\Users\USER\Downloads\ISSC-Django-main"

Set-Location $workingDir

Write-Host "Starting automated commit process..." -ForegroundColor Green
Write-Host "Working directory: $workingDir" -ForegroundColor Cyan

# Get all changed/untracked files from git status
Write-Host "`nGetting list of all files..." -ForegroundColor Yellow
$statusOutput = git status --porcelain
$fileArray = @()

foreach ($line in $statusOutput -split "`n") {
    if ($line -match '^\s*[AMDRC?!]+\s+(.+)$') {
        $path = $matches[1].Trim()
        if (Test-Path $path -PathType Leaf) {
            $fileArray += $path
        }
    }
}

$totalFiles = $fileArray.Count

Write-Host "Total files to commit: $totalFiles" -ForegroundColor Cyan

if ($totalFiles -eq 0) {
    Write-Host "No files to commit. Exiting." -ForegroundColor Yellow
    exit
}

Write-Host "`nCommitting files one by one...`n" -ForegroundColor Green

$commitCount = 0

foreach ($file in $fileArray) {
    $commitCount++
    
    # Add single file
    git add $file 2>&1 | Out-Null
    
    # Commit with "commit" message
    git commit -m "commit" 2>&1 | Out-Null
    
    Write-Host "[$commitCount/$totalFiles] Committed: $file" -ForegroundColor White
}

# Push all commits at once
Write-Host "`n>>> Pushing all commits to master..." -ForegroundColor Yellow
git push origin master
Write-Host ">>> Push completed!" -ForegroundColor Green

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Auto-commit process completed!" -ForegroundColor Green
Write-Host "Total commits created: $commitCount" -ForegroundColor Cyan
Write-Host "Total files committed: $totalFiles" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Green
