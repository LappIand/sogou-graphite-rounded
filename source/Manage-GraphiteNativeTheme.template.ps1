# Manual Graphite native theme-slot manager (version-agnostic). Default action: read-only Check.
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

function Resolve-ActiveVersionDirectory {
    param([string]$Root)
    # Prefer the directory of a running Sogou binary; the registry Version
    # value can point at a directory that an in-flight update has not created.
    $running = @()
    foreach ($name in @('SGTool', 'SogouCloud', 'SogouImeBroker', 'SGMyInput')) {
        foreach ($p in @(Get-Process -Name $name -ErrorAction SilentlyContinue)) {
            try { if ($p.Path) { $running += $p.Path } } catch { }
        }
    }
    foreach ($module in @('SogouTSF.dll', 'UIPlugin.dll')) {
        foreach ($p in @(Get-Process -ErrorAction SilentlyContinue)) {
            try {
                if ($p.Path -and $p.Path.StartsWith($Root, [StringComparison]::OrdinalIgnoreCase)) { $running += $p.Path }
            } catch { }
        }
    }
    $candidates = @()
    foreach ($path in $running) {
        $dir = Split-Path -Parent $path
        if (Test-Path -LiteralPath (Join-Path $dir 'Skin.dat')) { $candidates += $dir }
    }
    if ($candidates.Count -eq 0) {
        $dirs = @(Get-ChildItem -LiteralPath $Root -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '^\d+(\.\d+){1,}$' -and (Test-Path -LiteralPath (Join-Path $_.FullName 'Skin.dat')) })
        if ($dirs.Count -eq 0) { throw "No Sogou version directory with Skin.dat found under $Root. No files changed." }
        $candidates = @($dirs | Sort-Object { [version]($_.Name) } -Descending | Select-Object -First 1 | ForEach-Object FullName)
    }
    return @($candidates | Select-Object -Unique)[0]
}

$InstallPath = Resolve-ActiveVersionDirectory -Root $InstallRoot
$Version = Split-Path -Leaf $InstallPath
$BackupRoot = Join-Path $env:LOCALAPPDATA 'GraphiteSogouNativeTheme\backup'
$BackupPath = Join-Path $BackupRoot $Version

function Get-Sha256([string]$Path) {
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Assert-BackupManifest($saved) {
    if ([string]$saved.InstallPath -ne $InstallPath) { throw 'Backup was created for a different Sogou version directory. No files changed.' }
    if (@($saved.Files).Count -ne $SourceFiles.Count) { throw 'Unexpected backup file count. No files changed.' }
    $seen = @{}
    foreach ($item in $saved.Files) {
        $name = [string]$item.Name
        if (-not $SourceFiles.ContainsKey($name) -or $seen.ContainsKey($name)) { throw 'Unexpected backup file name. No files changed.' }
        $seen[$name] = $true
        if ([string]$item.Path -ne (Join-Path $InstallPath $name)) { throw 'Unexpected backup destination. No files changed.' }
        $backup = Join-Path $BackupPath $name
        if (-not (Test-Path -LiteralPath $backup)) { throw "Missing backup file: $name. No files changed." }
        if ((Get-Sha256 $backup) -ne [string]$item.SHA256) { throw "Backup checksum mismatch: $name. No files changed." }
    }
}

Write-Host "Sogou version directory: $InstallPath"
Write-Host "Backup directory: $BackupPath"

if ($Action -eq 'Check') {
    foreach ($name in $SourceFiles.Keys) {
        $target = Join-Path $InstallPath $name
        $stock = (Get-Sha256 $target) -eq $KnownStock[$name]
        $patch = (Get-Sha256 $target) -eq $ExpectedHashes[$SourceFiles[$name]]
        $state = if ($patch) { 'Graphite already applied' } elseif ($stock) { 'stock Sogou resource' } else { 'unrecognized resource' }
        Write-Host ("{0}: {1}" -f $name, $state)
    }
    $manifest = Join-Path $BackupPath 'manifest.json'
    Write-Host ("Backup manifest: {0}" -f ($(if (Test-Path -LiteralPath $manifest) { 'present' } else { 'none yet' })))
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
        $target = Join-Path $InstallPath $name
        if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw "Missing installed resource: $target" }
    }
    New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null
    $manifest = Join-Path $BackupPath 'manifest.json'
    if (-not (Test-Path -LiteralPath $manifest)) {
        foreach ($name in $SourceFiles.Keys) {
            if (Test-Path -LiteralPath (Join-Path $BackupPath $name)) { throw 'Incomplete earlier backup found. No files changed.' }
        }
        $items = @()
        foreach ($name in $SourceFiles.Keys) {
            $target = Join-Path $InstallPath $name
            $current = Get-Sha256 $target
            if ($current -ne $KnownStock[$name] -and $current -ne $ExpectedHashes[$SourceFiles[$name]]) {
                throw "Unrecognized current $name; refusing to overwrite without a known backup baseline."
            }
            $backup = Join-Path $BackupPath $name
            Copy-Item -LiteralPath $target -Destination $backup
            if ((Get-Sha256 $backup) -ne $current) { throw "Backup verification failed: $name" }
            $items += [pscustomobject]@{ Name = $name; Path = $target; SHA256 = $current }
        }
        [pscustomobject]@{ Version = $Version; InstallPath = $InstallPath; Files = $items } |
            ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifest -Encoding UTF8
    }
    $saved = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
    Assert-BackupManifest $saved
    try {
        foreach ($name in $SourceFiles.Keys) {
            Copy-Item -LiteralPath (Join-Path $Root $SourceFiles[$name]) -Destination (Join-Path $InstallPath $name) -Force
            if ((Get-Sha256 (Join-Path $InstallPath $name)) -ne $ExpectedHashes[$SourceFiles[$name]]) { throw "Installed checksum mismatch: $name" }
        }
    }
    catch {
        foreach ($item in $saved.Files) { Copy-Item -LiteralPath (Join-Path $BackupPath $item.Name) -Destination $item.Path -Force }
        throw
    }
    Write-Host "Applied Graphite light/dark resources to $Version (classic default slot)."
    Write-Host 'Next: choose the classic default skin in Sogou, then use Appearance -> light/dark/follow system.'
}
else {
    $manifest = Join-Path $BackupPath 'manifest.json'
    if (-not (Test-Path -LiteralPath $manifest)) { throw "No backup manifest for $Version. No files changed." }
    $saved = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
    Assert-BackupManifest $saved
    foreach ($item in $saved.Files) {
        Copy-Item -LiteralPath (Join-Path $BackupPath $item.Name) -Destination $item.Path -Force
        if ((Get-Sha256 $item.Path) -ne [string]$item.SHA256) { throw "Restore verification failed: $($item.Name)" }
    }
    Write-Host "Original $Version resources restored."
}
