[CmdletBinding()]
param(
    [string]$Ndk,
    [string]$Python,
    [ValidateRange(1,128)][int]$Jobs = 8,
    [string]$SpeedBackupRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
if (-not $Ndk) {
    $candidates = @(
        "$env:USERPROFILE\SambaAndroidBuild\toolchain\android-ndk-r30",
        $env:ANDROID_NDK_HOME,
        "$env:LOCALAPPDATA\Android\Sdk\ndk\30.0.16248370"
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath "$candidate\source.properties")) {
            if ((Get-Content -Raw -LiteralPath "$candidate\source.properties") -match 'Pkg.Revision\s*=\s*30\.0\.16248370\s') {
                $Ndk = $candidate
                break
            }
        }
    }
}
if (-not $Ndk) { throw 'NDK r30 not found. Pass -Ndk C:\path\android-ndk-r30.' }
if (-not $Python) {
    $bundled = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    if (Test-Path -LiteralPath $bundled) { $Python = $bundled }
    else { $Python = 'python' }
}
$previousNdk = $env:ANDROID_NDK_HOME
try {
    if (-not (Test-Path -LiteralPath (Join-Path $Ndk 'source.properties'))) { throw "NDK r30 (30.0.16248370) not found at $Ndk. Install it or pass -Ndk with its directory." }
    $revision = Get-Content -LiteralPath (Join-Path $Ndk 'source.properties') -Raw
    if ($revision -notmatch 'Pkg.Revision\s*=\s*30\.0\.16248370\s') { throw 'NDK r30 (30.0.16248370) required' }
    $env:ANDROID_NDK_HOME = $Ndk
    & $Python -X utf8 (Join-Path $PSScriptRoot 'build_native.py') android --jobs $Jobs
    if ($LASTEXITCODE -ne 0) { throw 'zstd static build or ELF validation failed' }
    $binary = Join-Path $PSScriptRoot 'out-r30/zstd'
    $hash = (Get-FileHash -LiteralPath $binary -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($SpeedBackupRoot) {
        $toolsFile = Join-Path $SpeedBackupRoot 'tools.sh'
        $repositoryTools = Join-Path $SpeedBackupRoot 'tools/tools.sh'
        if (Test-Path -LiteralPath $repositoryTools -PathType Leaf) { $toolsFile = $repositoryTools }
        $text = [IO.File]::ReadAllText($toolsFile)
        $table = [regex]::Match($text, "(?ms)^\tcat <<'SB_TOOL_SHA_TABLE'\r?\n.*?^SB_TOOL_SHA_TABLE\r?$")
        $pattern = '(?m)^zstd [0-9a-f]{64}(?=\r?$)'
        if (-not $table.Success -or [regex]::Matches($table.Value, $pattern).Count -ne 1) {
            throw 'Expected exactly one zstd SHA row in tools.sh'
        }
        $backup = $toolsFile + '.before-zstd-r30-' + [Guid]::NewGuid().ToString('N')
        Copy-Item -LiteralPath $toolsFile -Destination $backup
        $updated = [regex]::Replace($table.Value, $pattern, "zstd $hash")
        $utf8 = New-Object System.Text.UTF8Encoding($false)
        [IO.File]::WriteAllText($toolsFile, $text.Substring(0, $table.Index) + $updated + $text.Substring($table.Index + $table.Length), $utf8)
        Write-Host "Updated zstd SHA: $toolsFile"
    }
    Write-Host "PASS: ELF structure / arm64 / fully static / 16KiB alignment / API28-r30 identification; runtime compatibility untested"
    Write-Host "Output: $binary"
    Write-Host "SHA256: $hash"
} finally {
    if ($null -eq $previousNdk) { Remove-Item Env:ANDROID_NDK_HOME -ErrorAction SilentlyContinue }
    else { $env:ANDROID_NDK_HOME = $previousNdk }
}
