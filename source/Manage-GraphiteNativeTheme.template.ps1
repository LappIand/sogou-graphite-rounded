
# Manual native Graphite theme-slot manager. Default action is read-only Check.
[CmdletBinding()]
param(
    [ValidateSet('Install', 'Restore', 'Check')]
    [string]$Action = 'Check'
)
$ErrorActionPreference = 'Stop'
$TestedVersion = '16.6.0.4777'
$Root = $PSScriptRoot
$SourceFiles = @{
    'Skin.dat' = 'Graphite-Light.dat'
    'SkinDark.dat' = 'Graphite-Dark.dat'
}
$ExpectedHashes = @{
    'Graphite-Light.dat' = '4c3b6d9aea7e566542458c424211ba0e50e82183aa23f4c191279c00fb56abfd'
    'Graphite-Dark.dat' = 'b7f0aca32ac96f99b6675fa602d8489c4b309126a7abc11d29ebd15125ef414a'
}
$Registry = Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\WOW6432Node\SogouInput'
$Version = [string]$Registry.Version
$InstallRoot = [string]$Registry.'(default)'
if ($Version -ne $TestedVersion) {
    throw "This package was inspected for Sogou $TestedVersion; installed version is $Version. No files changed."
}
$InstallPath = Join-Path $InstallRoot $Version
$BackupPath = Join-Path $env:LOCALAPPDATA "GraphiteSogouNativeTheme\backup\$Version"

if ($Action -ne 'Restore') {
    foreach ($name in $SourceFiles.Keys) {
        $source = Join-Path $Root $SourceFiles[$name]
        $target = Join-Path $InstallPath $name
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Missing source: $source" }
        if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw "Missing installed resource: $target" }
        $hash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($hash -ne $ExpectedHashes[$SourceFiles[$name]]) { throw "Source checksum mismatch: $source" }
    }
}

function Assert-BackupManifest($saved) {
    if ($saved.InstallPath -ne $InstallPath -or $saved.Version -ne $Version) { throw 'Backup version/path mismatch. No installed files changed.' }
    if (@($saved.Files).Count -ne $SourceFiles.Count) { throw 'Unexpected backup file count. No installed files changed.' }
    $seen = @{}
    foreach ($item in $saved.Files) {
        if (-not $SourceFiles.ContainsKey([string]$item.Name) -or $seen.ContainsKey([string]$item.Name)) { throw 'Unexpected backup file name. No installed files changed.' }
        $seen[[string]$item.Name] = $true
        if ($item.Path -ne (Join-Path $InstallPath $item.Name)) { throw 'Unexpected backup destination. No installed files changed.' }
        $backup = Join-Path $BackupPath $item.Name
        if ((Get-FileHash -LiteralPath $backup -Algorithm SHA256).Hash -ne $item.SHA256) { throw 'Backup checksum mismatch. No installed files changed.' }
    }
}

Write-Host "Sogou version: $Version"
Write-Host "Native classic theme slot: $InstallPath"
Write-Host "Backup directory: $BackupPath"
if ($Action -eq 'Check') {
    foreach ($name in $SourceFiles.Keys) {
        $target = Join-Path $InstallPath $name
        Write-Host "$name SHA256: $((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash)"
    }
    Write-Host 'Check complete. No files changed.'
    exit 0
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Install and restore need an elevated PowerShell window. No files changed.'
}

if ($Action -eq 'Install') {
    if (-not (Test-Path -LiteralPath $BackupPath)) { New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null }
    $manifest = Join-Path $BackupPath 'manifest.json'
    if (-not (Test-Path -LiteralPath $manifest)) {
        # Stop if a partial previous backup exists; never overwrite backups.
        foreach ($name in $SourceFiles.Keys) {
            if (Test-Path -LiteralPath (Join-Path $BackupPath $name)) { throw 'Incomplete earlier backup found. No installed files changed.' }
        }
        $items = @()
        foreach ($name in $SourceFiles.Keys) {
            $target = Join-Path $InstallPath $name
            $backup = Join-Path $BackupPath $name
            Copy-Item -LiteralPath $target -Destination $backup
            $sourceHash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
            $backupHash = (Get-FileHash -LiteralPath $backup -Algorithm SHA256).Hash
            if ($sourceHash -ne $backupHash) { throw "Backup verification failed: $name" }
            $items += [pscustomobject]@{Name=$name;Path=$target;SHA256=$sourceHash}
        }
        [pscustomobject]@{Version=$Version;InstallPath=$InstallPath;Files=$items} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifest -Encoding UTF8
    }
    $saved = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
    Assert-BackupManifest $saved
    try {
        foreach ($name in $SourceFiles.Keys) {
            Copy-Item -LiteralPath (Join-Path $Root $SourceFiles[$name]) -Destination (Join-Path $InstallPath $name) -Force
            if ((Get-FileHash -LiteralPath (Join-Path $InstallPath $name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ExpectedHashes[$SourceFiles[$name]]) { throw "Installed checksum mismatch: $name" }
        }
    } catch {
        foreach ($item in $saved.Files) { Copy-Item -LiteralPath (Join-Path $BackupPath $item.Name) -Destination $item.Path -Force }
        throw
    }
    Write-Host 'Installed Graphite light/dark resources into the native classic theme slot.'
    Write-Host 'Next: choose the classic default skin in Sogou, then use its appearance light/dark/system switch.'
    Write-Host 'Restart applications or sign out/in to clear existing skin caches.'
} else {
    $manifest = Join-Path $BackupPath 'manifest.json'
    if (-not (Test-Path -LiteralPath $manifest)) { throw 'No backup manifest found. No files changed.' }
    $saved = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
    Assert-BackupManifest $saved
    foreach ($item in $saved.Files) {
        Copy-Item -LiteralPath (Join-Path $BackupPath $item.Name) -Destination $item.Path -Force
        if ((Get-FileHash -LiteralPath $item.Path -Algorithm SHA256).Hash -ne $item.SHA256) { throw "Restore verification failed: $($item.Name)" }
    }
    Write-Host 'Original native classic light/dark theme resources restored. Restart applications to clear cached skins.'
}
