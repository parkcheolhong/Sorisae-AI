$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$envPath = Join-Path $root '.env'
$certRoot = Join-Path $root 'certbot\local-certs'
$certFullchainPath = Join-Path $certRoot 'fullchain.pem'
$certPrivkeyPath = Join-Path $certRoot 'privkey.pem'

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

$httpPort = if ($env:NGINX_HTTP_PORT) { $env:NGINX_HTTP_PORT } else { Get-EnvValue -Path $envPath -Key 'NGINX_HTTP_PORT' }
$httpsPort = if ($env:NGINX_HTTPS_PORT) { $env:NGINX_HTTPS_PORT } else { Get-EnvValue -Path $envPath -Key 'NGINX_HTTPS_PORT' }
if (-not $httpPort) { $httpPort = '80' }
if (-not $httpsPort) { $httpsPort = '443' }

function Write-Section {
	param([string]$Message)
	Write-Host "`n[platform-start] $Message" -ForegroundColor Cyan
}

function Test-NonEmptyFile {
	param([string]$Path)
	return (Test-Path $Path) -and ((Get-Item $Path).Length -gt 0)
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

function Wait-ForHttpStatus {
	param(
		[string]$Url,
		[int]$TimeoutSeconds = 120
	)

	$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
	while ((Get-Date) -lt $deadline) {
		try {
			$response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
			if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
				return $response.StatusCode
			}
		}
		catch {
		}
		Start-Sleep -Seconds 2
	}

	throw "Timed out waiting for $Url"
}

function Open-UiInBrowser {
	param(
		[string[]]$Urls
	)

	$preferredBrowsers = @(
		'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
		'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
		'C:\Program Files\Google\Chrome\Application\chrome.exe',
		'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
	) | Where-Object { Test-Path $_ }

	foreach ($url in $Urls) {
		if ([string]::IsNullOrWhiteSpace($url)) {
			continue
		}

		foreach ($browserPath in $preferredBrowsers) {
			try {
				Start-Process -FilePath $browserPath -ArgumentList $url | Out-Null
				Write-Host "[platform-start] browser open requested via $([System.IO.Path]::GetFileName($browserPath)) -> $url" -ForegroundColor Green
				continue 2
			}
			catch {
			}
		}

		try {
			Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', 'start', '', $url -WindowStyle Hidden | Out-Null
			Write-Host "[platform-start] browser open requested -> $url" -ForegroundColor Green
			continue
		}
		catch {
		}

		try {
			Start-Process -FilePath 'explorer.exe' -ArgumentList $url | Out-Null
			Write-Host "[platform-start] browser open requested via explorer -> $url" -ForegroundColor Green
			continue
		}
		catch {
		}

		try {
			Start-Process $url | Out-Null
			Write-Host "[platform-start] browser open requested via shell -> $url" -ForegroundColor Green
		}
		catch {
			Write-Warning "[platform-start] failed to open UI automatically: $url :: $($_.Exception.Message)"
		}
	}
}

function Restore-LocalCertificates {
	if ((Test-NonEmptyFile $certFullchainPath) -and (Test-NonEmptyFile $certPrivkeyPath)) {
		Write-Section 'existing local certificates detected'
		return
	}

	Write-Section 'local certificates missing - attempting restore from existing artifacts'
	New-Item -ItemType Directory -Force -Path $certRoot | Out-Null

	$candidateDirectories = @()
	$liveCertDirectory = Join-Path $root 'certbot\conf\live\metanova1004.com'
	if (Test-Path $liveCertDirectory) {
		$candidateDirectories += (Get-Item $liveCertDirectory)
	}

	$artifactRoots = @(
		(Join-Path $root 'uploads\tmp\codeai_admin_runtime\admin_self_experiments'),
		(Join-Path $root 'uploads\tmp')
	) | Where-Object { Test-Path $_ }

	foreach ($artifactRoot in $artifactRoots) {
		$candidateDirectories += Get-ChildItem -Path $artifactRoot -Directory -Recurse -ErrorAction SilentlyContinue |
		Where-Object {
			(Test-Path (Join-Path $_.FullName 'certbot\local-certs\fullchain.pem')) -and
			(Test-Path (Join-Path $_.FullName 'certbot\local-certs\privkey.pem'))
		}
	}

	$bestCandidate = $candidateDirectories |
	ForEach-Object {
		$localCertDir = if ($_.FullName -like '*certbot\conf\live\metanova1004.com') { $_.FullName } else { Join-Path $_.FullName 'certbot\local-certs' }
		$fullchain = Join-Path $localCertDir 'fullchain.pem'
		$privkey = Join-Path $localCertDir 'privkey.pem'
		if ((Test-Path $fullchain) -and (Test-Path $privkey)) {
			[PSCustomObject]@{
				Directory     = $localCertDir
				Fullchain     = $fullchain
				Privkey       = $privkey
				LastWriteTime = (Get-Item $fullchain).LastWriteTime
			}
		}
	} |
	Where-Object { $_ } |
	Sort-Object LastWriteTime -Descending |
	Select-Object -First 1

	if ($bestCandidate) {
		Copy-Item $bestCandidate.Fullchain $certFullchainPath -Force
		Copy-Item $bestCandidate.Privkey $certPrivkeyPath -Force
		Write-Section "restored local certificates from $($bestCandidate.Directory)"
	}

	if ((Test-NonEmptyFile $certFullchainPath) -and (Test-NonEmptyFile $certPrivkeyPath)) {
		return
	}

	Write-Section 'existing certificate restore unavailable - attempting self-signed fallback'
	$openssl = Get-Command openssl.exe -ErrorAction SilentlyContinue
	if (-not $openssl) {
		throw 'Local certificates are missing and openssl.exe is unavailable. Restore existing certificates into certbot/local-certs or install OpenSSL for self-signed fallback.'
	}

	$opensslConfigPath = Join-Path $certRoot 'openssl.cnf'
	@"
[req]
default_bits = 2048
prompt = no
default_md = sha256
x509_extensions = v3_req
distinguished_name = dn

[dn]
C = KR
ST = Seoul
L = Seoul
O = DevAnalysis114
OU = Local Development
CN = metanova1004.com

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = metanova1004.com
DNS.2 = xn--114-2p7l635dz3bh5j.com
DNS.3 = api.xn--114-2p7l635dz3bh5j.com
DNS.4 = localhost
IP.1 = 127.0.0.1
"@ | Set-Content -Path $opensslConfigPath -Encoding ascii

	& $openssl.Source req -x509 -nodes -days 30 -newkey rsa:2048 -keyout $certPrivkeyPath -out $certFullchainPath -config $opensslConfigPath -extensions v3_req | Out-Host
	if ($LASTEXITCODE -ne 0) {
		throw 'OpenSSL self-signed fallback failed.'
	}

	if (-not ((Test-NonEmptyFile $certFullchainPath) -and (Test-NonEmptyFile $certPrivkeyPath))) {
		throw 'Self-signed fallback did not produce valid certificate files.'
	}
}

Push-Location $root
try {
	Restore-LocalCertificates

	Write-Section 'start backend stack'
	& (Join-Path $PSScriptRoot 'start_backend_stack.ps1')

	$ensureAdminScript = Join-Path $PSScriptRoot 'ensure_fixed_admin_account.ps1'
	if (Test-Path $ensureAdminScript) {
		if ([string]::IsNullOrWhiteSpace($env:FIXED_ADMIN_PASSWORD)) {
			Write-Warning '[platform-start] FIXED_ADMIN_PASSWORD is not set. Skipping fixed admin account ensure step.'
		}
		else {
			Write-Section 'ensure fixed admin account'
			& $ensureAdminScript
		}
	}
	else {
		Write-Warning '[platform-start] ensure_fixed_admin_account.ps1 is missing. Skipping admin ensure step.'
	}

	$availableServices = Get-ComposeServiceNames
	$frontendServices = @('frontend-marketplace', 'frontend-admin') | Where-Object { $availableServices -contains $_ }
	if ($frontendServices.Count -gt 0) {
		Write-Section ('start frontend services: ' + ($frontendServices -join ', '))
		docker compose up -d $frontendServices | Out-Host
	}

	if ($availableServices -contains 'nginx') {
		Write-Section 'start nginx gateway'
		docker compose up -d nginx | Out-Host
	}

	Write-Section 'wait for backend and gateway readiness'
	$backendStatus = Wait-ForHttpStatus -Url 'http://127.0.0.1:8000/health'
	Write-Host "[platform-start] backend /health -> HTTP $backendStatus" -ForegroundColor Green

	if ($availableServices -contains 'nginx') {
		$gatewayStatus = Wait-ForHttpStatus -Url "http://127.0.0.1:$httpPort/health"
		Write-Host "[platform-start] nginx /health -> HTTP $gatewayStatus" -ForegroundColor Green
		Open-UiInBrowser -Urls @(
			"http://127.0.0.1:3000/marketplace",
			"http://127.0.0.1:3005/admin"
		)
	}
}
finally {
	Pop-Location
}

Write-Host "`n[platform-start] done" -ForegroundColor Cyan
