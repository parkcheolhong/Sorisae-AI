param(
  [string]$Round = "R1"
)

$ErrorActionPreference = 'Stop'
$base = 'https://metanova1004.com/api/mobile/song-translation'
$tmpSong = [System.IO.Path]::GetTempFileName()
$tmpSample = [System.IO.Path]::GetTempFileName()

Set-Content -Path $tmpSong -Value "Hello`nThank you`nhelp me`n" -NoNewline -Encoding UTF8
[byte[]]$bytes = 0..255
[System.IO.File]::WriteAllBytes($tmpSample, $bytes)

try {
  $jobRaw = curl.exe -sS -X POST "$base/jobs" -F "target_language=ko" -F "source_language=auto" -F "quality=advanced" -F "mode=subtitle" -F "file=@$tmpSong;type=audio/mpeg;filename=song-$Round.mp3"
  $job = $jobRaw | ConvertFrom-Json
  $jobId = $job.job_id
  if (-not $jobId) { throw "job create failed: $jobRaw" }
  Write-Output "$Round JOB=$jobId"

  $status = ''
  $stage = ''
  for ($i = 0; $i -lt 40; $i++) {
    $st = Invoke-RestMethod -Uri "$base/jobs/$jobId" -Method Get -TimeoutSec 30
    $status = $st.status
    $stage = $st.stage
    if ($status -eq 'completed') { break }
    Start-Sleep -Seconds 2
  }
  Write-Output "$Round JOB_STATUS=$status/$stage"

  $consentBody = @{
    consent_version = '2026-05-voice-v1'
    voice_owner = 'self'
    allow_private_preview = $true
    allow_export_for_licensed_audio = $true
    user_id = "ops-verify-$Round"
  } | ConvertTo-Json -Compress
  $consent = Invoke-RestMethod -Uri "$base/voice-consents" -Method Post -ContentType 'application/json' -Body $consentBody -TimeoutSec 30
  $consentId = $consent.consent_id
  Write-Output "$Round CONSENT=$consentId"

  $profileRaw = curl.exe -sS -X POST "$base/voice-profiles" -F "consent_id=$consentId" -F "profile_label=ops-$Round" -F "sample=@$tmpSample;type=audio/m4a;filename=sample-$Round.m4a"
  $profile = $profileRaw | ConvertFrom-Json
  $profileId = $profile.voice_profile_id
  if (-not $profileId) { throw "profile create failed: $profileRaw" }
  Write-Output "$Round PROFILE=$profileId"

  $invalidBody = @{
    voice_profile_id = $profileId
    license_mode = 'policy_approved_distribution'
    preview_mode = 'translated_lyric_voice'
    output_scope = 'policy_approved_export'
    rights_acknowledged = $true
    approval_id = "invalid-approval-$Round"
  } | ConvertTo-Json -Compress
  $previewInvalid = Invoke-RestMethod -Uri "$base/jobs/$jobId/voice-preview" -Method Post -ContentType 'application/json' -Body $invalidBody -TimeoutSec 30
  Write-Output "$Round INVALID_GATE=$($previewInvalid.gate_status)/$($previewInvalid.effective_output_scope)/allowed=$($previewInvalid.policy_allowed)"

  $privateBody = @{
    voice_profile_id = $profileId
    license_mode = 'private_preview_unverified'
    preview_mode = 'translated_lyric_voice'
    output_scope = 'private_preview'
    rights_acknowledged = $false
  } | ConvertTo-Json -Compress
  $previewPrivate = Invoke-RestMethod -Uri "$base/jobs/$jobId/voice-preview" -Method Post -ContentType 'application/json' -Body $privateBody -TimeoutSec 30
  $hasAudioField = $previewPrivate.PSObject.Properties.Name -contains 'preview_audio_available'
  Write-Output "$Round PRIVATE_GATE=$($previewPrivate.gate_status)/allowed=$($previewPrivate.policy_allowed)"
  Write-Output "$Round AUDIO_FIELD_PRESENT=$hasAudioField"
  if ($hasAudioField) {
    Write-Output "$Round AUDIO_AVAILABLE=$($previewPrivate.preview_audio_available)"
  }
  Write-Output "$Round PREVIEW_ID=$($previewPrivate.preview_id)"
}
finally {
  Remove-Item $tmpSong -ErrorAction SilentlyContinue
  Remove-Item $tmpSample -ErrorAction SilentlyContinue
}
