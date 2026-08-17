param(
    [string]$WebSocketUrl = "wss://metanova1004.com/api/llm/ws",
    [int]$TimeoutSec = 15
)

$ErrorActionPreference = "Stop"

function Test-WebSocketHandshake {
    param(
        [string]$Url,
        [int]$TimeoutSeconds
    )

    $cts = [System.Threading.CancellationTokenSource]::new([TimeSpan]::FromSeconds($TimeoutSeconds))
    $ws = [System.Net.WebSockets.ClientWebSocket]::new()

    try {
        $uri = [Uri]$Url
        $connectTask = $ws.ConnectAsync($uri, $cts.Token)
        $connectTask.GetAwaiter().GetResult()

        if ($ws.State -ne [System.Net.WebSockets.WebSocketState]::Open) {
            throw "handshake failed: state=$($ws.State)"
        }

        return [pscustomobject]@{
            ok = $true
            state = [string]$ws.State
            url = $Url
        }
    }
    finally {
        if ($ws.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
            $closeCts = [System.Threading.CancellationTokenSource]::new([TimeSpan]::FromSeconds(3))
            try {
                $ws.CloseAsync(
                    [System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure,
                    "done",
                    $closeCts.Token
                ).GetAwaiter().GetResult()
            }
            catch {
            }
            $closeCts.Dispose()
        }
        $ws.Dispose()
        $cts.Dispose()
    }
}

$result = Test-WebSocketHandshake -Url $WebSocketUrl -TimeoutSeconds $TimeoutSec
$result | ConvertTo-Json -Depth 3
