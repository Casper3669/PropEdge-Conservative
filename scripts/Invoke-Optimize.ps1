param(
  [string]$BaseUrl = "http://127.0.0.1:8080",
  [string]$Market = "NBA",
  [ValidateSet("standard","flex")] [string]$Mode = "flex",
  [int]$Bankroll = 100
)

$ErrorActionPreference = "Stop"
$today = Get-Date -Format "yyyy-MM-dd"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$proj = Split-Path -Parent $root
$data = Join-Path $proj "data"
$outf = Join-Path $data "lineups_$today.json"
$propsPath = Join-Path $data "props_sample.csv"

if (-not (Test-Path $propsPath)) {
  "name,player,team,market,line,price
NBA,LeBron James,LAL,PTS,25.5,0.53
NBA,Anthony Davis,LAL,REB,12.5,0.49" | Set-Content -Path $propsPath
  Write-Host "🆕 Created sample props_sample.csv"
}

$props = Get-Content -Raw -Path $propsPath
$payload = @{
  slate_date = $today
  market = $Market
  mode = $Mode
  bankroll = $Bankroll
  csv_props = $props
} | ConvertTo-Json -Depth 6

try {
  $res = Invoke-RestMethod -Uri "$BaseUrl/optimize" -Method Post -ContentType 'application/json' -Body $payload -TimeoutSec 60
  $res | ConvertTo-Json -Depth 10 | Set-Content -Path $outf -Encoding UTF8
  Write-Host "✅ Optimize complete. Saved to $outf"
} catch {
  Write-Host "❌ Optimize call failed: $($_.Exception.Message)" -ForegroundColor Red
}
