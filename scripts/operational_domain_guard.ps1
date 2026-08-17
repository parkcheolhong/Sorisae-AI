Set-StrictMode -Version Latest

function Get-OperationalDomainConfig {
    return [pscustomobject]@{
        MarketplaceDomain   = 'metanova1004.com'
        AdminUnicodeDomain  = '개발분석114.com'
        AdminPunycodeDomain = 'xn--114-2p7l635dz3bh5j.com'
        AllowedDomains      = @(
            'metanova1004.com',
            '개발분석114.com',
            'xn--114-2p7l635dz3bh5j.com'
        )
    }
}

function Convert-ToCanonicalDomain {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Domain
    )

    $value = $Domain.Trim().ToLowerInvariant()
    if ($value -eq '개발분석114.com') {
        return 'xn--114-2p7l635dz3bh5j.com'
    }
    return $value
}

function Assert-OperationalDomains {
    param(
        [Parameter(Mandatory = $true)]
        [string]$MarketplaceDomain,
        [Parameter(Mandatory = $true)]
        [string]$AdminDomain,
        [string]$ScriptName = 'verification script'
    )

    $cfg = Get-OperationalDomainConfig
    $market = Convert-ToCanonicalDomain -Domain $MarketplaceDomain
    $admin = Convert-ToCanonicalDomain -Domain $AdminDomain

    if ($market -ne $cfg.MarketplaceDomain) {
        throw "[$ScriptName] marketplace domain must be $($cfg.MarketplaceDomain), actual=$MarketplaceDomain"
    }

    if ($admin -ne $cfg.AdminPunycodeDomain) {
        throw "[$ScriptName] admin domain must be $($cfg.AdminUnicodeDomain) ($($cfg.AdminPunycodeDomain)), actual=$AdminDomain"
    }
}

function Assert-AllowedOperationalUrl {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [string]$ScriptName = 'verification script'
    )

    $cfg = Get-OperationalDomainConfig
    $uri = [uri]$Url
    $urlHost = Convert-ToCanonicalDomain -Domain $uri.Host

    $allowedCanonical = @($cfg.AllowedDomains | ForEach-Object { Convert-ToCanonicalDomain -Domain $_ })
    if ($allowedCanonical -notcontains $urlHost) {
        throw "[$ScriptName] non-operational domain is blocked: $($uri.Host)"
    }
}
