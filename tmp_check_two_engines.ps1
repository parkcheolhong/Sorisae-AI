$ErrorActionPreference = 'Stop'
$TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMTljYXNoQG5hdmVyLmNvbSJ9.A82QOF91hXhgqe0wVmdp8owADYBj_LLlljrahl8n_Y8"
$h = @{ Authorization = "Bearer $TOKEN"; "Content-Type" = "application/json" }

foreach ($eng in @("divine", "music_chat_friend")) {
  $body = @{ engine_type = $eng; context = @{} } | ConvertTo-Json -Compress
  try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/marketplace/sorisae/dispatch" -Method POST -Headers $h -Body $body -TimeoutSec 20
    Write-Host "[$eng] status=$($r.status)"
    ($r | ConvertTo-Json -Depth 8)
  }
  catch {
    Write-Host "[$eng] FAIL"
    if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
      Write-Host $_.ErrorDetails.Message
    }
    else {
      Write-Host $_.Exception.Message
    }
  }
}
