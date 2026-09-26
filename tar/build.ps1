[CmdletBinding()]
param(
    [string]$Ndk,
    [string]$Msys = 'C:/msys64',
    [string]$Python,
    [ValidateRange(1,128)][int]$Jobs = 8,
    [string]$AsciiBuildRoot
)
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
$buildArgs = @('-X', 'utf8', (Join-Path $PSScriptRoot 'build.py'), '--ndk', $Ndk, '--msys', $Msys, '--jobs', "$Jobs")
if ($AsciiBuildRoot) { $buildArgs += @('--stage-root', $AsciiBuildRoot) }
& $Python @buildArgs
if ($LASTEXITCODE -ne 0) { throw 'Static tar build failed; see out/build.log and retained build stage.' }
