#requires -Version 5.1
# SPDX-License-Identifier: GPL-3.0-only
[CmdletBinding()]
param(
    [string]$Ndk,
    [string]$Msys = 'C:\msys64',
    [string]$Python,
    [ValidateRange(1,128)][int]$Jobs = 8,
    [string]$WorkRoot,
    [string]$DeviceSerial,
    [string]$Adb = 'C:\platform-tools\adb.exe',
    [string]$Gpg = 'C:\Program Files\Git\usr\bin\gpg.exe',
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8

# Each child has its own environment discovery and can be used independently.
$targets = @(
    @{ Name = 'zstd'; Output = 'out-r30'; Binaries = @('zstd'); Metadata = 'out-r30/BUILD_INFO.json' },
    @{ Name = 'tar'; Output = 'out'; Binaries = @('tar'); Metadata = 'out/BUILD_MANIFEST.json' },
    @{ Name = 'busybox'; Output = 'out'; Binaries = @('busybox'); Metadata = 'out/BUILD_MANIFEST.json' },
    @{ Name = 'samba'; Output = 'dist/android-arm64-size';
       Binaries = @('smbclient','smbd','samba-dcerpcd','rpcd_classic','rpcd_lsad','rpcd_winreg');
       Metadata = 'dist/android-arm64-size/build-metadata.json' }
)
foreach ($target in $targets) {
    $entry = Join-Path $PSScriptRoot ($target.Name + '/build.ps1')
    if (-not (Test-Path -LiteralPath $entry -PathType Leaf)) {
        throw "Missing component build script: $entry"
    }
}
if ($WorkRoot) {
    $WorkRoot = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($WorkRoot)
}
$built = @()
$step = 0
foreach ($target in $targets) {
    $step++
    $name = $target.Name
    $folder = Join-Path $PSScriptRoot $name
    $entry = Join-Path $folder 'build.ps1'
    $childArgs = @{ Jobs = $Jobs }
    if ($Ndk) { $childArgs.Ndk = $Ndk }
    if ($Python -and $name -ne 'samba') { $childArgs.Python = $Python }
    if ($name -ne 'zstd') { $childArgs.Msys = $Msys }
    if ($name -eq 'tar' -and $WorkRoot) {
        $childArgs.AsciiBuildRoot = Join-Path $WorkRoot 'tar'
    }
    if ($name -eq 'busybox') {
        if ($WorkRoot) { $childArgs.CacheRoot = Join-Path $WorkRoot 'busybox' }
        if ($Clean) { $childArgs.Clean = $true }
    }
    if ($name -eq 'samba') {
        $childArgs.BuildProfile = 'size'
        $childArgs.BuildScope = 'all'
        $childArgs.Adb = $Adb
        $childArgs.Gpg = $Gpg
        if ($DeviceSerial) { $childArgs.DeviceSerial = $DeviceSerial }
        if ($WorkRoot) { $childArgs.CacheRoot = Join-Path $WorkRoot 'samba' }
        if ($Clean) { $childArgs.Clean = $true }
    }
    Write-Host "[$step/4] Building $name..."
    try {
        & $entry @childArgs
        $metadata = Join-Path $folder $target.Metadata
        if (-not (Test-Path -LiteralPath $metadata -PathType Leaf)) {
            throw 'The component did not publish build metadata.'
        }
        foreach ($binaryName in $target.Binaries) {
            $binaryRelative = $name + '/' + $target.Output + '/' + $binaryName
            $binary = Join-Path $PSScriptRoot $binaryRelative
            if (-not (Test-Path -LiteralPath $binary -PathType Leaf)) {
                throw "The component did not publish $binaryName."
            }
            $built += [pscustomobject]@{
                component = $name
                name = $binaryName
                binary = $binaryRelative
                metadata = $name + '/' + $target.Metadata
                bytes = (Get-Item -LiteralPath $binary).Length
                sha256 = (Get-FileHash -LiteralPath $binary -Algorithm SHA256).Hash.ToLowerInvariant()
            }
        }
    } catch {
        throw "Build stopped at ${name}. Combined out/ was not updated. $($_.Exception.Message)"
    }
}

# Collect only after all four builders have succeeded.
$output = Join-Path $PSScriptRoot 'out'
New-Item -ItemType Directory -Path $output -Force | Out-Null
$checksums = @()
foreach ($item in $built) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $item.binary) -Destination (Join-Path $output $item.name) -Force
    $checksums += $item.sha256 + '  ' + $item.name
}
foreach ($target in $targets) {
    $metadata = Join-Path $PSScriptRoot ($target.Name + '/' + $target.Metadata)
    Copy-Item -LiteralPath $metadata -Destination (Join-Path $output ($target.Name + '-build.json')) -Force
}
[IO.File]::WriteAllText((Join-Path $output 'SHA256SUMS.txt'), (($checksums -join "`n") + "`n"), $utf8)
$manifest = [ordered]@{
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
    target = 'aarch64-linux-android28'
    ndk_revision = '30.0.16248370'
    components = $built
    runtime_tests = 'Samba preserves its existing ADB configure probes and final smbclient --version check. No additional functional tests are run.'
}
[IO.File]::WriteAllText((Join-Path $output 'BUILD_MANIFEST.json'), (($manifest | ConvertTo-Json -Depth 6) + "`n"), $utf8)
Write-Host "All four builds completed. Nine binaries and SHA256: $output"
