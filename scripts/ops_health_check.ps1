param(
	[int]$TimeoutSec = 15,
	[string]$AdminDomain = 'metanova1004.com',
	[string]$MarketplaceDomain = 'xn--114-2p7l635dz3bh5j.com'
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$envPath = Join-Path $root '.env'

function Write-Section {
	param([string]$Message)
	Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Add-Result {
	param(
		[System.Collections.Generic.List[object]]$ResultList,
		[string]$Name,
		[bool]$Passed,
		[string]$Detail
	)

	$ResultList.Add([PSCustomObject]@{
		Check = $Name
		Passed = $Passed
		Detail = $Detail
	}) | Out-Null
}

function Get-EnvValue {
	param(
		[string]$Path,
		[string]$Key
	)

	if (-not (Test-Path $Path -PathType Leaf)) {
		return $null
	}

	try {
		$line = Get-Content -Path $Path -ErrorAction Stop | Where-Object { $_ -match "^$Key=" } | Select-Object -First 1
	}
	catch {
		return $null
	}

	if (-not $line) {
		return $null
	}

	return $line.Split('=', 2)[1]
}

function Get-ComposeServiceNames {
	Push-Location $root
	try {
		return @(docker compose config --services)
	}
	finally {
		Pop-Location
	}
}

function Get-ComposePsOutput {
	Push-Location $root
	try {
		$jsonLines = @(docker compose ps --format json)
		if ($jsonLines.Count -eq 0) {
			return @()
		}

		$items = @()
		foreach ($jsonLine in $jsonLines) {
			if ([string]::IsNullOrWhiteSpace($jsonLine)) {
				continue
			}

			$items += ($jsonLine | ConvertFrom-Json)
		}

		return @($items)
	}
	finally {
		Pop-Location
	}
}

function Get-CurlStatusCode {
	param(
		[string]$Url,
		[string]$HostHeader,
		[switch]$Insecure
	)

	$arguments = @('-s', '-o', 'NUL', '-w', '%{http_code}')
	if ($HostHeader) {
		$arguments += @('-H', "Host: $HostHeader")
	}
	if ($Insecure) {
		$arguments += '-k'
	}
	$arguments += $Url

	$output = & curl.exe @arguments
	return ($output | Out-String).Trim()
}

function Test-ListeningPort {
	param([int]$Port)
	return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1)
}

$results = New-Object System.Collections.Generic.List[object]
$httpPort = Get-EnvValue -Path $envPath -Key 'NGINX_HTTP_PORT'
$httpsPort = Get-EnvValue -Path $envPath -Key 'NGINX_HTTPS_PORT'
if (-not $httpPort) { $httpPort = '8080' }
if (-not $httpsPort) { $httpsPort = '8443' }

$availableServices = Get-ComposeServiceNames
$composePs = Get-ComposePsOutput

Write-Section 'Compose configuration'
try {
	Push-Location $root
	try {
		docker compose config > $null
	}
	finally {
		Pop-Location
	}
	Add-Result -ResultList $results -Name 'docker compose config' -Passed $true -Detail 'OK'
}
catch {
	Add-Result -ResultList $results -Name 'docker compose config' -Passed $false -Detail $_.Exception.Message
}

foreach ($service in @('postgres', 'redis', 'qdrant', 'minio', 'backend', 'video-worker', 'frontend-admin', 'nginx')) {
	if ($availableServices -contains $service) {
		$serviceInfo = $composePs | Where-Object { $_.Service -eq $service } | Select-Object -First 1
		$serviceDetail = if ($serviceInfo) {
			$state = if ($serviceInfo.State) { $serviceInfo.State } else { 'unknown' }
			$health = if ($serviceInfo.Health) { $serviceInfo.Health } else { 'n/a' }
			$status = if ($serviceInfo.Status) { $serviceInfo.Status } else { 'status 없음' }
			"state=$state, health=$health, status=$status"
		}
		else {
			'서비스 정보 없음'
		}
		$serviceOk = ($serviceInfo -ne $null) -and (($serviceInfo.State -match 'running') -or ($serviceInfo.Status -match 'Up'))
		Add-Result -ResultList $results -Name "compose service $service" -Passed $serviceOk -Detail $serviceDetail
	}
}

Write-Section 'Backend health endpoints'
foreach ($target in @(
	@{ Name = 'backend /health'; Url = 'http://127.0.0.1:8000/health'; Expected = '200'; Host = $null; Insecure = $false },
	@{ Name = 'backend /docs'; Url = 'http://127.0.0.1:8000/docs'; Expected = '200'; Host = $null; Insecure = $false },
	@{ Name = 'backend /openapi.json'; Url = 'http://127.0.0.1:8000/openapi.json'; Expected = '200'; Host = $null; Insecure = $false }
)) {
	try {
		$code = Get-CurlStatusCode -Url $target.Url -HostHeader $target.Host -Insecure:([bool]$target.Insecure)
		Add-Result -ResultList $results -Name $target.Name -Passed ($code -eq $target.Expected) -Detail "HTTP $code"
	}
	catch {
		Add-Result -ResultList $results -Name $target.Name -Passed $false -Detail $_.Exception.Message
	}
}

if ($availableServices -contains 'nginx') {
	Write-Section 'Gateway health and UI routes'
	$httpListening = Test-ListeningPort -Port ([int]$httpPort)
	$httpsListening = Test-ListeningPort -Port ([int]$httpsPort)
	Add-Result -ResultList $results -Name "nginx http port $httpPort listening" -Passed $true -Detail ($(if ($httpListening) { "port $httpPort" } else { "skipped: port $httpPort not published on host" }))
	Add-Result -ResultList $results -Name "nginx https port $httpsPort listening" -Passed $true -Detail ($(if ($httpsListening) { "port $httpsPort" } else { "skipped: port $httpsPort not published on host" }))

	if ($httpListening -or $httpsListening) {
		foreach ($target in @(
			@{ Name = 'nginx /health (http)'; Url = "http://127.0.0.1:$httpPort/health"; Expected = '200'; Host = 'localhost'; Insecure = $false; Enabled = $httpListening },
			@{ Name = 'nginx /health (https)'; Url = "https://127.0.0.1:$httpsPort/health"; Expected = '200'; Host = 'localhost'; Insecure = $true; Enabled = $httpsListening },
			@{ Name = 'ui /marketplace (https)'; Url = "https://127.0.0.1:$httpsPort/marketplace"; Expected = '200'; Host = 'localhost'; Insecure = $true; Enabled = $httpsListening },
			@{ Name = 'ui /admin (https)'; Url = "https://127.0.0.1:$httpsPort/admin"; Expected = '200'; Host = 'localhost'; Insecure = $true; Enabled = $httpsListening }
		)) {
			if (-not $target.Enabled) {
				Add-Result -ResultList $results -Name $target.Name -Passed $true -Detail 'skipped: corresponding host port not published'
				continue
			}

			try {
				$code = Get-CurlStatusCode -Url $target.Url -HostHeader $target.Host -Insecure:([bool]$target.Insecure)
				Add-Result -ResultList $results -Name $target.Name -Passed ($code -eq $target.Expected) -Detail "HTTP $code"
			}
			catch {
				Add-Result -ResultList $results -Name $target.Name -Passed $false -Detail $_.Exception.Message
			}
		}
	}

	Write-Section 'Operational domain routes'
	foreach ($target in @(
		@{ Name = 'ops admin /health'; Url = "https://$AdminDomain/health"; Expected = '200'; Host = $null; Insecure = $false },
		@{ Name = 'ops admin ui /admin/llm'; Url = "https://$MarketplaceDomain/admin/llm"; Expected = '200'; Host = $null; Insecure = $false },
		@{ Name = 'ops marketplace /marketplace'; Url = "https://$MarketplaceDomain/marketplace"; Expected = '200'; Host = $null; Insecure = $false }
	)) {
		try {
			$code = Get-CurlStatusCode -Url $target.Url -HostHeader $target.Host -Insecure:([bool]$target.Insecure)
			Add-Result -ResultList $results -Name $target.Name -Passed ($code -eq $target.Expected) -Detail "HTTP $code"
		}
		catch {
			Add-Result -ResultList $results -Name $target.Name -Passed $false -Detail $_.Exception.Message
		}
	}
}

Write-Section 'Health Summary'
$results | Format-Table -AutoSize | Out-Host
$failed = @($results | Where-Object { -not $_.Passed })
if ($failed.Count -gt 0) {
	Write-Host "`n[health] failed checks: $($failed.Count)" -ForegroundColor Red
	exit 1
}

Write-Host "`n[health] all checks passed" -ForegroundColor Green
