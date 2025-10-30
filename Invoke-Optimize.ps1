param(
  [string]$ApiUrl   = "http://localhost:8080",
  [string]$PropsCsv = ".\data\props_sample.csv",
  [double]$Bankroll = 50
)

# Build an array of objects directly from CSV (no intermediate JSON string)
$rows  = Import-Csv -Path $PropsCsv
$props = foreach ($r in $rows) {
  [pscustomobject]@{
    source            = $r.source
    platform          = $r.platform
    sport             = $r.sport
    game_datetime_utc = $r.game_datetime_utc
    player            = $r.player
    team              = $r.team
    opponent          = $r.opponent
    market            = $r.market
    line              = [double]$r.line
    side              = $r.side
    proj_mean         = ($(if ($r.proj_mean) { [double]$r.proj_mean } else { $null }))
    prob_over         = ($(if ($r.prob_over) { [double]$r.prob_over } else { $null }))
  }
}

$payload = @{ bankroll = $Bankroll; props = $props } | ConvertTo-Json -Depth 6

Invoke-RestMethod -Uri "$ApiUrl/optimize" -Method POST -Body $payload -ContentType "application/json" |
  ConvertTo-Json -Depth 6
