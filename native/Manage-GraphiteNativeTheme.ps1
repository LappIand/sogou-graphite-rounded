# Manual Graphite native theme-slot manager.
# Default action: read-only Check. Install patches every existing version directory.
[CmdletBinding()]
param(
    [ValidateSet('Install', 'Restore', 'Check')]
    [string]$Action = 'Check'
)
$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$SourceFiles = @{
    'Skin.dat' = 'Graphite-Light.dat'
    'SkinDark.dat' = 'Graphite-Dark.dat'
}
$ExpectedHashes = @{
    'Graphite-Light.dat' = 'a9ed1f34bc2b748f9a281b8333710b6e58c177869f591b0487b5f9b7884eda73'
    'Graphite-Dark.dat' = '8055f71929abce1cf1e60c0cbf1980449347e32394352a37d32229c955766387'
}
# Hash of the untouched stock resources this patcher knows how to back up.
$KnownStock = @{
    'Skin.dat' = 'd2182b6e1d43315357d08808f18b4770566394cc1e004b639d99f43461f02eb6'
    'SkinDark.dat' = '8c7a181d09c43e21bf339ee5d7f723fac55c88a6ed5054bb5ee6ea68c47c0811'
}

$Registry = Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\WOW6432Node\SogouInput'
$InstallRoot = [string]$Registry.'(default)'
if (-not (Test-Path -LiteralPath $InstallRoot -PathType Container)) { throw "Sogou install root not found: $InstallRoot. No files changed." }
$BackupRoot = Join-Path $env:LOCALAPPDATA 'GraphiteSogouNativeTheme\backup'

function Get-Sha256([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }

function Get-VersionDirectories {
    param([string]$Root)
    @(Get-ChildItem -LiteralPath $Root -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^\d+(\.\d+){1,}$' -and (Test-Path -LiteralPath (Join-Path $_.FullName 'Skin.dat')) } |
        Sort-Object { [version]$_.Name } -Descending)
}

function Assert-BackupManifest($saved, [string]$InstallPath, [string]$BackupPath) {
    if ([string]$saved.InstallPath -ne $InstallPath) { throw "Backup belongs to a different directory: $InstallPath. No files changed." }
    if (@($saved.Files).Count -ne $SourceFiles.Count) { throw "Unexpected backup file count in $InstallPath. No files changed." }
    $seen = @{}
    foreach ($item in $saved.Files) {
        $name = [string]$item.Name
        if (-not $SourceFiles.ContainsKey($name) -or $seen.ContainsKey($name)) { throw 'Unexpected backup file name. No files changed.' }
        $seen[$name] = $true
        if ([string]$item.Path -ne (Join-Path $InstallPath $name)) { throw 'Unexpected backup destination. No files changed.' }
        $backup = Join-Path $BackupPath $name
        if (-not (Test-Path -LiteralPath $backup)) { throw "Missing backup file: $backup. No files changed." }
        if ((Get-Sha256 $backup) -ne [string]$item.SHA256) { throw "Backup checksum mismatch: $backup. No files changed." }
    }
}

function Get-State([string]$Path, [string]$SourceName) {
    $hash = Get-Sha256 $Path
    if ($hash -eq $ExpectedHashes[$SourceName]) { return 'patched' }
    $key = Split-Path -Leaf $Path
    if ($hash -eq $KnownStock[$key]) { return 'stock' }
    return 'unknown'
}

$directories = Get-VersionDirectories -Root $InstallRoot
if ($directories.Count -eq 0) { throw "No Sogou version directory with Skin.dat found under $InstallRoot. No files changed." }

if ($Action -eq 'Check') {
    foreach ($dir in $directories) {
        Write-Host ("{0}  ({1})" -f $dir.Name, $dir.FullName)
        foreach ($name in $SourceFiles.Keys) {
            Write-Host ("   {0}: {1}" -f $name, (Get-State (Join-Path $dir.FullName $name) $SourceFiles[$name]))
        }
        $manifest = Join-Path (Join-Path $BackupRoot $dir.Name) 'manifest.json'
        Write-Host ("   backup manifest: {0}" -f ($(if (Test-Path -LiteralPath $manifest) { 'present' } else { 'none' })))
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
    foreach ($name in $SourceFiles.Keys) {
        $source = Join-Path $Root $SourceFiles[$name]
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Missing source: $source" }
        if ((Get-Sha256 $source) -ne $ExpectedHashes[$SourceFiles[$name]]) { throw "Source checksum mismatch: $source" }
    }
    foreach ($dir in $directories) {
        $installPath = $dir.FullName
        $version = $dir.Name
        $backupPath = Join-Path $BackupRoot $version
        $states = @{}
        $skip = $false
        foreach ($name in $SourceFiles.Keys) {
            $target = Join-Path $installPath $name
            if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw "Missing installed resource: $target" }
            $states[$name] = Get-State $target $SourceFiles[$name]
            if ($states[$name] -eq 'unknown') {
                $skip = $true
                Write-Warning "Skipping $version : $name is neither stock nor Graphite. Nothing replaced in this directory."
            }
        }
        if ($skip) { continue }
        New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
        $manifest = Join-Path $backupPath 'manifest.json'
        if (-not (Test-Path -LiteralPath $manifest)) {
            foreach ($name in $SourceFiles.Keys) {
                if (Test-Path -LiteralPath (Join-Path $backupPath $name)) { throw "Incomplete earlier backup in $backupPath. No files changed." }
            }
            $items = @()
            foreach ($name in $SourceFiles.Keys) {
                $target = Join-Path $installPath $name
                $current = Get-Sha256 $target
                $backup = Join-Path $backupPath $name
                Copy-Item -LiteralPath $target -Destination $backup
                if ((Get-Sha256 $backup) -ne $current) { throw "Backup verification failed: $backup" }
                $items += [pscustomobject]@{ Name = $name; Path = $target; SHA256 = $current }
            }
            [pscustomobject]@{ Version = $version; InstallPath = $installPath; Files = $items } |
                ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifest -Encoding UTF8
        }
        $saved = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
        Assert-BackupManifest $saved $installPath $backupPath
        try {
            foreach ($name in $SourceFiles.Keys) {
                Copy-Item -LiteralPath (Join-Path $Root $SourceFiles[$name]) -Destination (Join-Path $installPath $name) -Force
                if ((Get-Sha256 (Join-Path $installPath $name)) -ne $ExpectedHashes[$SourceFiles[$name]]) { throw "Installed checksum mismatch: $installPath\$name" }
            }
        }
        catch {
            foreach ($item in $saved.Files) { Copy-Item -LiteralPath (Join-Path $backupPath $item.Name) -Destination $item.Path -Force }
            throw
        }
        Write-Host "Applied Graphite to $version"
    }
    Write-Host 'Done. In Sogou choose the classic default skin, then Appearance -> light/dark/follow system.'
    Write-Host 'Re-run Install after a Sogou upgrade; each version is backed up separately.'
}
else {
    $restored = 0
    foreach ($dir in $directories) {
        $installPath = $dir.FullName
        $backupPath = Join-Path $BackupRoot $dir.Name
        $manifest = Join-Path $backupPath 'manifest.json'
        if (-not (Test-Path -LiteralPath $manifest)) { continue }
        $saved = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
        Assert-BackupManifest $saved $installPath $backupPath
        foreach ($item in $saved.Files) {
            Copy-Item -LiteralPath (Join-Path $backupPath $item.Name) -Destination $item.Path -Force
            if ((Get-Sha256 $item.Path) -ne [string]$item.SHA256) { throw "Restore verification failed: $($item.Name)" }
        }
        Write-Host "Restored original resources for $($dir.Name)"
        $restored++
    }
    if ($restored -eq 0) { throw "No backup manifest found under $BackupRoot. No files changed." }
}
