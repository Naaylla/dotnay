# Build dist\dotnay.exe with PyInstaller, then dist\dotnay-setup.exe with Inno Setup.
# Usage: powershell -ExecutionPolicy Bypass -File tools\build_installer.ps1
#        powershell -ExecutionPolicy Bypass -File tools\build_installer.ps1 -SkipAppBuild

param(
    [switch]$SkipAppBuild
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot

try {
    if (-not $SkipAppBuild) {
        Write-Host 'Building dist\dotnay.exe with PyInstaller...'
        python -m PyInstaller --noconfirm dotnay.spec
        if ($LASTEXITCODE -ne 0) {
            throw "PyInstaller failed with exit code $LASTEXITCODE."
        }
    }

    $appExe = Join-Path $projectRoot 'dist\dotnay.exe'
    if (-not (Test-Path -LiteralPath $appExe)) {
        throw "Missing $appExe. Run this script without -SkipAppBuild."
    }

    $iscc = $null
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) {
        $iscc = $command.Source
    }

    if (-not $iscc) {
        $searchRoots = @($env:ProgramFiles, ${env:ProgramFiles(x86)}, (Join-Path $env:LOCALAPPDATA 'Programs'))
        foreach ($searchRoot in $searchRoots) {
            if (-not $searchRoot -or -not (Test-Path -LiteralPath $searchRoot)) { continue }
            $found = Get-ChildItem -LiteralPath $searchRoot -Directory -Filter 'Inno Setup*' -ErrorAction SilentlyContinue |
                Sort-Object Name -Descending |
                ForEach-Object { Join-Path $_.FullName 'ISCC.exe' } |
                Where-Object { Test-Path -LiteralPath $_ } |
                Select-Object -First 1
            if ($found) {
                $iscc = $found
                break
            }
        }
    }

    if (-not $iscc) {
        $uninstallKeys = @(
            'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
            'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall',
            'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'
        )
        foreach ($key in $uninstallKeys) {
            $entry = Get-ChildItem -LiteralPath $key -ErrorAction SilentlyContinue |
                ForEach-Object { Get-ItemProperty -LiteralPath $_.PSPath -ErrorAction SilentlyContinue } |
                Where-Object { $_.DisplayName -like 'Inno Setup*' -and $_.InstallLocation } |
                Select-Object -First 1
            if ($entry) {
                $candidate = Join-Path $entry.InstallLocation 'ISCC.exe'
                if (Test-Path -LiteralPath $candidate) {
                    $iscc = $candidate
                    break
                }
            }
        }
    }

    if (-not $iscc) {
        throw 'Inno Setup (6 or newer) was not found. Install it from https://jrsoftware.org/isdl.php, then run this script again.'
    }

    $scriptPath = Join-Path $projectRoot 'installer\dotnay.iss'
    Write-Host "Compiling installer with $iscc ..."
    & $iscc $scriptPath
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup failed with exit code $LASTEXITCODE."
    }

    $setup = Join-Path $projectRoot 'dist\dotnay-setup.exe'
    if (-not (Test-Path -LiteralPath $setup)) {
        throw "Expected $setup, but it was not created."
    }

    $info = Get-Item -LiteralPath $setup
    Write-Host ''
    Write-Host "Installer ready: $($info.FullName)"
    Write-Host ('Size: {0:N1} MB' -f ($info.Length / 1MB))
}
finally {
    Pop-Location
}
