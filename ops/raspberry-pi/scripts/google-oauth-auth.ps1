# Interactive Google OAuth for n8n Google Calendar credential.
# Requires ops/raspberry-pi/.env: GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, N8N_API_KEY.
# Optional: GOOGLE_CALENDAR_CREDENTIAL_ID (default Sc6NYYy2HJCpDM78), N8N_BASE_URL.
# GCP OAuth client must allow redirect URI: http://127.0.0.1:8765/

param(
    [int]$Port = 8765,
    [string]$CredentialId = $env:GOOGLE_CALENDAR_CREDENTIAL_ID
)

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFile = Join-Path (Split-Path -Parent $scriptDir) '.env'

function Load-DotEnv {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        throw "Missing $Path — copy .env.example and fill GOOGLE_OAUTH_* and N8N_API_KEY."
    }
    Get-Content $Path | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
        $name, $value = $_ -split '=', 2
        $name = $name.Trim()
        $value = $value.Trim().Trim('"').Trim("'")
        if ($name) { Set-Item -Path "Env:$name" -Value $value }
    }
}

function Update-DotEnvValue {
    param(
        [string]$Path,
        [string]$Key,
        [string]$Value
    )
    $lines = Get-Content $Path
    $found = $false
    $updated = foreach ($line in $lines) {
        if ($line -match "^\s*$([regex]::Escape($Key))\s*=") {
            $found = $true
            "$Key=$Value"
        } else {
            $line
        }
    }
    if (-not $found) {
        $updated += "$Key=$Value"
    }
    Set-Content -Path $Path -Value $updated -Encoding utf8
}

Load-DotEnv -Path $envFile

$clientId = $env:GOOGLE_OAUTH_CLIENT_ID
$clientSecret = $env:GOOGLE_OAUTH_CLIENT_SECRET
$apiKey = $env:N8N_API_KEY
$baseUrl = if ($env:N8N_BASE_URL) { $env:N8N_BASE_URL.TrimEnd('/') } else { 'https://n8n.bentenberge.com' }

if (-not $CredentialId) { $CredentialId = 'Sc6NYYy2HJCpDM78' }
if (-not $clientId -or -not $clientSecret) { throw 'Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET in .env' }
if (-not $apiKey) { throw 'Set N8N_API_KEY in .env' }

$scope = 'https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/calendar.events'
$redirectUri = "http://127.0.0.1:$Port/"
$state = [guid]::NewGuid().ToString('N')

$authUrl = 'https://accounts.google.com/o/oauth2/v2/auth?' + (
    @{
        client_id = $clientId
        redirect_uri = $redirectUri
        response_type = 'code'
        scope = $scope
        access_type = 'offline'
        prompt = 'consent'
        state = $state
    }.GetEnumerator() | ForEach-Object { "{0}={1}" -f $_.Key, [uri]::EscapeDataString([string]$_.Value) }
) -join '&'

Write-Host "Starting local callback listener on $redirectUri"
Write-Host "Opening browser for Google consent..."
Write-Host "If the browser does not open, visit:"
Write-Host $authUrl
Write-Host

$listener = [System.Net.HttpListener]::new()
$listener.Prefixes.Add($redirectUri)
$listener.Start()

Start-Process $authUrl | Out-Null

$context = $listener.GetContext()
$request = $context.Request
$response = $context.Response

$query = [System.Web.HttpUtility]::ParseQueryString($request.Url.Query)
$code = $query['code']
$returnedState = $query['state']
$errorParam = $query['error']

$body = if ($errorParam) {
    "<html><body><h1>Authorization failed</h1><p>$errorParam</p></body></html>"
} elseif (-not $code -or $returnedState -ne $state) {
    '<html><body><h1>Authorization failed</h1><p>Missing code or state mismatch.</p></body></html>'
} else {
    '<html><body><h1>Google authorized</h1><p>You can close this tab and return to PowerShell.</p></body></html>'
}

$buffer = [System.Text.Encoding]::UTF8.GetBytes($body)
$response.ContentLength64 = $buffer.Length
$response.OutputStream.Write($buffer, 0, $buffer.Length)
$response.Close()
$listener.Stop()

if ($errorParam) { throw "Google OAuth error: $errorParam" }
if (-not $code) { throw 'No authorization code received.' }

Write-Host 'Exchanging authorization code for tokens...'

$tokenBody = @{
    code = $code
    client_id = $clientId
    client_secret = $clientSecret
    redirect_uri = $redirectUri
    grant_type = 'authorization_code'
}

$tokenResponse = Invoke-RestMethod -Method Post -Uri 'https://oauth2.googleapis.com/token' `
    -ContentType 'application/x-www-form-urlencoded' `
    -Body $tokenBody

if (-not $tokenResponse.refresh_token) {
    throw 'Google did not return a refresh_token. Revoke app access at https://myaccount.google.com/permissions and run again (prompt=consent).'
}

$expiresAt = (Get-Date).AddSeconds([int]$tokenResponse.expires_in).ToUniversalTime().ToString('o')

$patchBody = @{
    data = @{
        clientId = $clientId
        clientSecret = $clientSecret
        oauthTokenData = @{
            accessToken = $tokenResponse.access_token
            refreshToken = $tokenResponse.refresh_token
            expiresIn = [int]$tokenResponse.expires_in
            expiresAt = $expiresAt
            tokenType = $tokenResponse.token_type
            scope = $tokenResponse.scope
        }
    }
} | ConvertTo-Json -Depth 6

$headers = @{
    'X-N8N-API-KEY' = $apiKey
    'Content-Type' = 'application/json'
}

Invoke-RestMethod -Method Patch -Uri "$baseUrl/api/v1/credentials/$CredentialId" `
    -Headers $headers -Body $patchBody | Out-Null

Update-DotEnvValue -Path $envFile -Key 'GOOGLE_OAUTH_REFRESH_TOKEN' -Value $tokenResponse.refresh_token

Write-Host "Updated n8n credential $CredentialId on $baseUrl"
Write-Host "Saved GOOGLE_OAUTH_REFRESH_TOKEN to $envFile"
Write-Host 'Test Nathan in Telegram or run a calendar workflow in n8n.'
