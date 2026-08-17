$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Write-Section {
	param([string]$Message)
	Write-Host "`n[platform-stop] $Message" -ForegroundColor Cyan
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

Push-Location $root
try {
	$availableServices = Get-ComposeServiceNames
	$stopOrder = @(
		'frontend-marketplace',
		'frontend-admin',
		'nginx',
		'video-worker',
		'backend',
		'postgres',
		'redis',
		'qdrant',
		'minio'
	) | Where-Object { $availableServices -contains $_ }

	if ($stopOrder.Count -eq 0) {
		Write-Warning '[platform-stop] no compose services matched the platform stop order.'
	}
	else {
		Write-Section ('stop services: ' + ($stopOrder -join ', '))
		docker compose stop @stopOrder | Out-Host
	}
}
finally {
	Pop-Location
}

Write-Host "`n[platform-stop] done" -ForegroundColor Cyan
