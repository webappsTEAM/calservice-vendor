<#
.SYNOPSIS
    Compresses the codebase into a clean, lightweight zip archive.
.DESCRIPTION
    Excludes installables (node_modules, venvs, .git, caches, dist, build)
    while explicitly preserving .env files.
.EXAMPLE
    .\zip_codebase.ps1
.EXAMPLE
    .\zip_codebase.ps1 -Target both
.EXAMPLE
    .\zip_codebase.ps1 -Output "my_backup.zip"
#>

param(
    [string]$Output = "",
    [ValidateSet("customer", "vendor", "both", "all")]
    [string]$Target = "both",
    [switch]$ExcludeEnv,
    [switch]$ExcludeAssets,
    [switch]$IncludeGit,
    [switch]$IncludeVenv,
    [switch]$IncludeNodeModules,
    [switch]$DryRun
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pyScript = Join-Path $scriptDir "zip_codebase.py"

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue

if (-not $pythonCmd) {
    # Fallback to backend venv python if system python is not in PATH
    $venvPy = Join-Path $scriptDir "backend\venv\Scripts\python.exe"
    if (Test-Path $venvPy) {
        $pythonCmd = $venvPy
    } else {
        Write-Error "Python was not found in PATH or venv. Please ensure Python is installed."
        exit 1
    }
} else {
    $pythonCmd = "python"
}

$argsList = @()
if ($Output) { $argsList += "-o", $Output }
if ($Target) { $argsList += "--target", $Target }
if ($ExcludeEnv) { $argsList += "--exclude-env" }
if ($ExcludeAssets) { $argsList += "--exclude-assets" }
if ($IncludeGit) { $argsList += "--include-git" }
if ($IncludeVenv) { $argsList += "--include-venv" }
if ($IncludeNodeModules) { $argsList += "--include-node-modules" }
if ($DryRun) { $argsList += "--dry-run" }

& $pythonCmd $pyScript @argsList
