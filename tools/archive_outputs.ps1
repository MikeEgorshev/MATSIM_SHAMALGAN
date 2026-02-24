param(
    [string]$Root = ".",
    [string]$ArchiveDirName = "archive-outputs",
    [int]$KeepLatest = 1
)

$ErrorActionPreference = "Stop"

if ($KeepLatest -lt 0) {
    throw "KeepLatest must be >= 0."
}

$rootPath = (Resolve-Path -Path $Root).Path
$archivePath = Join-Path $rootPath $ArchiveDirName

if (-not (Test-Path -Path $archivePath)) {
    New-Item -ItemType Directory -Path $archivePath | Out-Null
}

# Archive folders that are run outputs while skipping build/source folders.
$outputDirs = Get-ChildItem -Path $rootPath -Directory |
    Where-Object {
        $_.Name -like "output*" -and
        $_.Name -ne $ArchiveDirName -and
        $_.Name -ne "output" -and
        $_.Name -ne "target"
    } |
    Sort-Object LastWriteTime -Descending

if ($outputDirs.Count -le $KeepLatest) {
    Write-Host "Nothing to archive. Found $($outputDirs.Count) output folder(s), KeepLatest=$KeepLatest."
    return
}

$toArchive = $outputDirs | Select-Object -Skip $KeepLatest

foreach ($dir in $toArchive) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $destination = Join-Path $archivePath ("{0}-{1}" -f $dir.Name, $stamp)
    Move-Item -Path $dir.FullName -Destination $destination
    Write-Host ("Archived: {0} -> {1}" -f $dir.FullName, $destination)
}

Write-Host "Done."
