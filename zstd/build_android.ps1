# Compatibility entry point; the authoritative static builder is build.ps1.
[CmdletBinding()]
param(
    [string]$NdkRoot,
    [string]$Python,
    [ValidateRange(1,128)][int]$Jobs = 8,
    [string]$SpeedBackupRoot
)
$ErrorActionPreference = 'Stop'
& "$PSScriptRoot/build.ps1" -Ndk $NdkRoot -Python $Python -Jobs $Jobs -SpeedBackupRoot $SpeedBackupRoot
