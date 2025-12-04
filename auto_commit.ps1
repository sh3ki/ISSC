# Auto Commit Script - Commits all files in batches of 1
# Pushes to master every 150 commits

$ErrorActionPreference = "Continue"
$workingDir = "C:\Users\USER\Downloads\ISSC-Django-main"

# Change to the repository directory
Set-Location $workingDir

Write-Host "Starting automated commit process..." -ForegroundColor Green
Write-Host "Working directory: $workingDir" -ForegroundColor Cyan

# Get all changed/untracked files
Write-Host "`nGetting list of all files..." -ForegroundColor Yellow

# Use git status to get all files (new, modified, deleted)
$statusOutput = git status --porcelain
$fileArray = @()

foreach ($line in $statusOutput -split "`n") {
    if ($line -match '^\?\?\s+(.+)$') {
        # Untracked file or directory
        $path = $matches[1].Trim()
        
        # If it's a directory, get all files in it recursively
        if (Test-Path $path -PathType Container) {
            $filesInDir = Get-ChildItem -Path $path -Recurse -File | ForEach-Object { $_.FullName.Replace("$workingDir\", "").Replace("\", "/") }
            $fileArray += $filesInDir
        } else {
            $fileArray += $path
        }
    } elseif ($line -match '^\s*[AMDRC?!]\s+(.+)$') {
        # Modified, added, deleted, renamed, copied files
        $path = $matches[1].Trim()
        if (-not (Test-Path $path -PathType Container)) {
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

# Batch settings
$batchSize = 1
$pushInterval = 150
$commitCount = 0
$currentBatch = @()

Write-Host "`nStarting batch commits (1 files per commit)..." -ForegroundColor Green
Write-Host "Will push to master every 150 commits`n" -ForegroundColor Green

foreach ($file in $fileArray) {
    $currentBatch += $file
    
    # When batch reaches 1 files OR it's the last file
    if ($currentBatch.Count -eq $batchSize -or $file -eq $fileArray[-1]) {
        $commitCount++
        
        # Add files in current batch (suppress all output)
        foreach ($f in $currentBatch) {
            git add $f 2>&1 | Out-Null
        }
        
        # Commit with simple message (suppress all output)
        git commit -m "commit" 2>&1 | Out-Null
        
        $filesInCommit = $currentBatch.Count
        Write-Host "[$commitCount] Committed $filesInCommit files" -ForegroundColor White
        
        # Push every 150 commits
        if ($commitCount % 150 -eq 0) {
            Write-Host "`n>>> Pushing to master (150 commits reached)..." -ForegroundColor Yellow
            git push origin master 2>&1 | Out-Null
            Write-Host ">>> Push completed!`n" -ForegroundColor Green
        }
        
        # Clear batch for next iteration
        $currentBatch = @()
    }
}

# Final push if there are remaining commits
$remainingCommits = $commitCount % 150
if ($remainingCommits -gt 0) {
    Write-Host "`n>>> Final push to master ($remainingCommits remaining commits)..." -ForegroundColor Yellow
    git push origin master 2>&1 | Out-Null
    Write-Host ">>> Push completed!" -ForegroundColor Green
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Auto-commit process completed!" -ForegroundColor Green
Write-Host "Total commits created: $commitCount" -ForegroundColor Cyan
Write-Host "Total files committed: $totalFiles" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Green
