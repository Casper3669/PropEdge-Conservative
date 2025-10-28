<#
    PowerShell script to update the PropEdge‑Conservative repository with NHL support and an optional cross‑sport tier configuration.

    This script performs the following actions:
    1. Clones the PropEdge‑Conservative repository and checks out a new feature branch.
    2. Adds canonical stat mappings for NHL props to ingest/schema.py.
    3. Adds sport detection for NHL in ingest/excel_loaders.py.
    4. (Optional) Updates the README to mention NHL/CFB support.
    5. Commits the changes and pushes the branch to the origin.

    You can run this script in PowerShell (e.g. on Windows with Git installed).  Adjust paths and branch names as desired.
#>

# Configuration: repository URL and branch name
$repoUrl = "https://github.com/Casper3669/PropEdge-Conservative.git"
$branchName = "feature/nhl-cfb-tiers"

# Clone the repository
if (-Not (Test-Path -Path "PropEdge-Conservative")) {
    git clone $repoUrl
}

Set-Location -Path "PropEdge-Conservative"

# Create and switch to the new branch
git checkout -b $branchName

# ===== Step 1: Update canonical stats for NHL in ingest/schema.py =====
$schemaFile = "ingest\schema.py"
if (-Not (Test-Path $schemaFile)) {
    Write-Error "Cannot find $schemaFile. Make sure you are in the correct repository."
    exit 1
}

# Read the file into an array of lines
$schemaLines = Get-Content -Path $schemaFile -Raw -Encoding UTF8 -Split "`n"

# Find the closing brace of the CANONICAL_STATS dictionary
$closingIndex = $schemaLines | ForEach-Object { $_ } | Select-String -Pattern "^\s+\}" | Select-Object -First 1
if (-Not $closingIndex) {
    Write-Error "Could not find the end of the CANONICAL_STATS dictionary in $schemaFile."
    exit 1
}
$insertAt = $closingIndex.LineNumber - 1

# Define the NHL entries to insert
$nhlEntries = @(
    "    # Hockey (NHL)",
    "    'shots on goal': 'Shots on Goal',",
    "    'sog': 'Shots on Goal',",
    "    'goals': 'Goals',",
    "    'assists': 'Assists',",
    "    'points': 'Points',",
    "    'saves': 'Saves',",
    "    'goals allowed': 'Goals Allowed',",
    "    'blocked shots': 'Blocked Shots',",
    "    'penalty minutes': 'Penalty Minutes',"
)

# Insert the new entries before the closing brace
$updatedSchema = @()
$updatedSchema += $schemaLines[0..($insertAt-1)]
$updatedSchema += $nhlEntries
$updatedSchema += $schemaLines[$insertAt..($schemaLines.Length-1)]

# Write the updated content back to the file
Set-Content -Path $schemaFile -Value ($updatedSchema -join "`n") -Encoding UTF8

# ===== Step 2: Update Excel loader to detect NHL files =====
$loaderFile = "ingest\excel_loaders.py"
if (-Not (Test-Path $loaderFile)) {
    Write-Error "Cannot find $loaderFile. Make sure you are in the correct repository."
    exit 1
}
$loaderLines = Get-Content -Path $loaderFile -Raw -Encoding UTF8 -Split "`n"

# Find the line that detects NCAAB and insert NHL detection afterwards
$pattern = "elif 'NCAAB'"
$found = $false
$newLoaderLines = @()
for ($i = 0; $i -lt $loaderLines.Length; $i++) {
    $line = $loaderLines[$i]
    $newLoaderLines += $line
    if (-Not $found -and $line -match $pattern) {
        # Insert the NHL detection block on the next line
        $newLoaderLines += "    elif 'NHL' in filename or 'HOCKEY' in filename:"
        $newLoaderLines += "        sport_hint = 'NHL'"
        $found = $true
    }
}

# If pattern not found, warn but proceed
if (-Not $found) {
    Write-Warning "Could not find 'elif \"NCAAB\"' pattern in $loaderFile; NHL detection not inserted."
}

Set-Content -Path $loaderFile -Value ($newLoaderLines -join "`n") -Encoding UTF8

# ===== Step 3: Optional README update =====
$readmeFile = "README.md"
if (Test-Path $readmeFile) {
    Add-Content -Path $readmeFile -Value "`n`nNow supports NHL and CFB props with a cross‑sport tier system." -Encoding UTF8
}

# ===== Step 4: Commit and push changes =====
git add ingest/schema.py ingest/excel_loaders.py README.md
git commit -m "Add NHL canonical stats and detection; update README"
git push -u origin $branchName

Write-Host "Update complete. Review your branch and create a pull request." -ForegroundColor Green