# Installs the Global MC_L4 package, waits for the startup git fetch to finish,
# and starts the bundled Python GUI. A grey Start App button is a failure.
param(
    [Parameter(Mandatory = $true)][string]$Dest,
    [Parameter(Mandatory = $true)][string]$Installer
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class Mcl4SmokeWin32 {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extra);
}
"@

$Evidence = Join-Path $Dest 'smoke-evidence'

function Save-Screen([string]$Path) {
    $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
    $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose()
    $bitmap.Dispose()
    Write-Host "screenshot=$Path bytes=$((Get-Item $Path).Length)"
}

function Get-SmokeLogs {
    @(
        Get-ChildItem -Path $Dest -Recurse -Include *.log,stdout*.txt,stderr*.txt -ErrorAction SilentlyContinue
    ) | Where-Object { $_ -and $_.Length -gt 0 -and $_.FullName -notlike "$Evidence*" }
}

function Show-SmokeLogs {
    $logs = Get-SmokeLogs | Sort-Object LastWriteTime -Descending
    foreach ($log in $logs | Select-Object -First 4) {
        Write-Host "----- $($log.FullName) -----"
        Get-Content -LiteralPath $log.FullName -Tail 80 | Write-Host
    }
}

function Get-LogBaseline {
    $baseline = @{}
    foreach ($log in (Get-SmokeLogs)) {
        $baseline[$log.FullName] = $log.Length
    }
    return $baseline
}

function Get-NewLogText([hashtable]$Baseline) {
    $parts = New-Object System.Collections.Generic.List[string]
    foreach ($log in (Get-SmokeLogs)) {
        $start = 0L
        if ($Baseline.ContainsKey($log.FullName)) { $start = [int64]$Baseline[$log.FullName] }
        if ($log.Length -le $start) { continue }
        $stream = [System.IO.File]::Open(
            $log.FullName,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Read,
            [System.IO.FileShare]::ReadWrite
        )
        try {
            [void]$stream.Seek($start, [System.IO.SeekOrigin]::Begin)
            $reader = New-Object System.IO.StreamReader($stream)
            $parts.Add($reader.ReadToEnd())
        } finally {
            $stream.Dispose()
        }
    }
    return ($parts -join "`n")
}

function Test-LogPattern([hashtable]$Baseline, [string]$Pattern) {
    return (Get-NewLogText $Baseline) -match $Pattern
}

function Wait-LogPattern([System.Diagnostics.Process]$Proc, [hashtable]$Baseline, [string]$Pattern, [int]$Seconds) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    do {
        if (Test-LogPattern $Baseline $Pattern) { return $true }
        if ($Proc.HasExited) { return $false }
        Start-Sleep -Seconds 3
    } while ((Get-Date) -lt $deadline)
    return (Test-LogPattern $Baseline $Pattern)
}

function Find-EnabledStartButton([string]$Path) {
    $source = [System.Drawing.Bitmap]::FromFile($Path)
    $bitmap = New-Object System.Drawing.Bitmap $source.Width, $source.Height, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.DrawImage($source, 0, 0, $source.Width, $source.Height)
    $graphics.Dispose()
    $source.Dispose()
    $rect = New-Object System.Drawing.Rectangle 0, 0, $bitmap.Width, $bitmap.Height
    $data = $bitmap.LockBits($rect, [System.Drawing.Imaging.ImageLockMode]::ReadOnly, $bitmap.PixelFormat)
    $stride = $data.Stride
    $bytes = New-Object byte[] ($stride * $bitmap.Height)
    [System.Runtime.InteropServices.Marshal]::Copy($data.Scan0, $bytes, 0, $bytes.Length)
    $bitmap.UnlockBits($data)
    $count = 0
    $minX = [int]($bitmap.Width * 0.45)
    $maxY = [Math]::Max(0, $bitmap.Height - 60)
    $left = $bitmap.Width
    $top = $bitmap.Height
    $right = 0
    $bottom = 0
    $sumX = 0
    $sumY = 0
    for ($y = 0; $y -lt $maxY; $y += 2) {
        for ($x = $minX; $x -lt $bitmap.Width; $x += 2) {
            $index = ($y * $stride) + ($x * 4)
            $blue = $bytes[$index]
            $green = $bytes[$index + 1]
            $red = $bytes[$index + 2]
            # Enabled MUI success button: light #059669 or dark #34d399.
            if ($green -gt 110 -and $green -lt 230 -and $red -lt 90 -and $blue -gt 60 -and $blue -lt 190 -and ($green - $red) -gt 60 -and ($green - $blue) -gt 10) {
                $count++
                $sumX += $x
                $sumY += $y
                if ($x -lt $left) { $left = $x }
                if ($y -lt $top) { $top = $y }
                if ($x -gt $right) { $right = $x }
                if ($y -gt $bottom) { $bottom = $y }
            }
        }
    }
    $bitmap.Dispose()
    $boxWidth = $right - $left
    $boxHeight = $bottom - $top
    Write-Host "enabled-start-pixels=$count box=${boxWidth}x${boxHeight}"
    if ($count -lt 25 -or $boxWidth -lt 30 -or $boxWidth -gt 280 -or $boxHeight -lt 12 -or $boxHeight -gt 80) {
        return $null
    }
    return @{ X = [int]($sumX / $count); Y = [int]($sumY / $count) }
}

function Click-Screen([int]$X, [int]$Y) {
    [Mcl4SmokeWin32]::SetCursorPos($X, $Y) | Out-Null
    Start-Sleep -Milliseconds 100
    [Mcl4SmokeWin32]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
    [Mcl4SmokeWin32]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
}

function Get-BundledPython {
    Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'pythonw.exe'" |
        Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($Dest, [System.StringComparison]::OrdinalIgnoreCase) }
}

function Stop-SmokeProcesses([System.Diagnostics.Process]$Launcher) {
    foreach ($python in (Get-BundledPython)) {
        Write-Host "stopping bundled $($python.Name) pid=$($python.ProcessId)"
        Stop-Process -Id $python.ProcessId -Force -ErrorAction SilentlyContinue
    }
    if ($Launcher -and -not $Launcher.HasExited) {
        Write-Host "stopping launcher pid=$($Launcher.Id)"
        Stop-Process -Id $Launcher.Id -Force -ErrorAction SilentlyContinue
    }
}

function Assert-UserFiles([string]$Kept, [string]$ConfigHash, [string]$TaskHash) {
    $keptText = Get-Content -LiteralPath $Kept -Raw
    if ($keptText -notmatch 'keep-this-user-file') {
        throw 'Startup removed the preserved user file'
    }
    $config = Join-Path $Dest 'data\apps\MC_L4\working\config.py'
    $task = Join-Path $Dest 'data\apps\MC_L4\working\src\task\BaseWWTask.py'
    if ((Get-FileHash -LiteralPath $config -Algorithm SHA256).Hash -ne $ConfigHash) {
        throw 'Startup replaced the bundled config.py'
    }
    if ((Get-FileHash -LiteralPath $task -Algorithm SHA256).Hash -ne $TaskHash) {
        throw 'Startup replaced the bundled task source'
    }
}

function Invoke-LauncherScenario([string]$Name, [string]$Kept, [string]$ConfigHash, [string]$TaskHash) {
    $stdout = Join-Path $Dest "stdout-$Name.txt"
    $stderr = Join-Path $Dest "stderr-$Name.txt"
    $baseline = Get-LogBaseline
    $env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = '--force-renderer-accessibility'
    $proc = Start-Process -FilePath (Join-Path $Dest 'MC_L4.exe') -WorkingDirectory $Dest -PassThru `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    Write-Host "scenario=$Name launcher=$($proc.Id)"
    try {
        if (-not (Wait-LogPattern $proc $baseline 'Repository already exists' 90)) {
            Show-SmokeLogs
            throw "$Name did not open the packaged repository"
        }
        foreach ($forbidden in @('not a valid git repository', 'Attempting to clone', 'Deleting app artifacts')) {
            if (Test-LogPattern $baseline $forbidden) {
                Show-SmokeLogs
                throw "$Name startup matched forbidden log: $forbidden"
            }
        }
        if (-not (Test-LogPattern $baseline 'Finished loading app details\. MC_L4 true')) {
            Show-SmokeLogs
            throw "$Name did not load the installed app"
        }
        if (-not (Test-LogPattern $baseline 'running with tauri ui')) {
            Show-SmokeLogs
            throw "$Name did not start the Tauri window"
        }
        if (-not (Test-LogPattern $baseline 'Clone MC_L4 from https://github.com/sule99999/ok-wuthering-waves\.git')) {
            Show-SmokeLogs
            throw "$Name did not use the packaged fork"
        }
        if (-not (Wait-LogPattern $proc $baseline 'Packaged repository is ready; skipping startup fetch\.' 60)) {
            Show-SmokeLogs
            throw "$Name still started the unbounded startup fetch"
        }
        if (Test-LogPattern $baseline 'Fetching updates for existing repository') {
            Show-SmokeLogs
            throw "$Name still fetches every branch before Start App"
        }
        if (-not (Wait-LogPattern $proc $baseline 'get_tags_and_current_version done for MC_L4: None' 60)) {
            Show-SmokeLogs
            throw "$Name did not finish version resolution with no tag"
        }
        Start-Sleep -Seconds 8
        $proc.Refresh()
        if ($proc.MainWindowHandle -ne [IntPtr]::Zero) {
            [Mcl4SmokeWin32]::SetForegroundWindow($proc.MainWindowHandle) | Out-Null
            Start-Sleep -Milliseconds 500
        }
        $launcherShot = Join-Path $Evidence "launcher-$Name.png"
        Save-Screen $launcherShot
        $button = Find-EnabledStartButton $launcherShot
        if (-not $button) {
            throw "$Name Start App is not visibly enabled after fetch"
        }
        Write-Host "clicking Start App at $($button.X),$($button.Y)"
        Click-Screen $button.X $button.Y
        if (-not (Wait-LogPattern $proc $baseline 'Attempting to start app:' 20)) {
            Show-SmokeLogs
            throw "$Name click did not invoke start_app"
        }
        if (-not (Wait-LogPattern $proc $baseline 'Python Path:' 30)) {
            Show-SmokeLogs
            throw "$Name did not launch the bundled Python runtime"
        }
        $pythonDeadline = (Get-Date).AddSeconds(180)
        $pythonWindow = $false
        do {
            $python = @(Get-Process -Name pythonw,python -ErrorAction SilentlyContinue |
                Where-Object { $_ -and $_.Path -and $_.Path.StartsWith($Dest, [System.StringComparison]::OrdinalIgnoreCase) -and $_.MainWindowHandle -ne 0 })
            foreach ($candidate in $python) {
                if (-not $candidate) { continue }
                $candidate.Refresh()
                Write-Host "python-window pid=$($candidate.Id) title=$($candidate.MainWindowTitle)"
                if ($candidate.MainWindowTitle) {
                    [Mcl4SmokeWin32]::SetForegroundWindow($candidate.MainWindowHandle) | Out-Null
                    $pythonWindow = $true
                    break
                }
            }
            if ($pythonWindow) { break }
            if (Test-LogPattern $baseline 'Script run Error') { break }
            Start-Sleep -Seconds 3
        } while ((Get-Date) -lt $pythonDeadline)
        Start-Sleep -Seconds 3
        $pythonShot = Join-Path $Evidence "python-$Name.png"
        Save-Screen $pythonShot
        if (Test-LogPattern $baseline 'Script run Error') {
            Show-SmokeLogs
            throw "$Name Python GUI exited with an error"
        }
        if (-not $pythonWindow) {
            Show-SmokeLogs
            throw "$Name bundled Python process did not open a window"
        }
        Assert-UserFiles $Kept $ConfigHash $TaskHash
    } finally {
        Stop-SmokeProcesses $proc
        Start-Sleep -Seconds 2
    }
}

if (-not (Test-Path -LiteralPath $Installer)) {
    throw "Installer is missing: $Installer"
}
if (Test-Path -LiteralPath $Dest) {
    cmd /c "rmdir /s /q $Dest"
}
Write-Host "installing $Installer to $Dest"
cmd /c "`"$Installer`" /S /D=$Dest"
$installDeadline = (Get-Date).AddMinutes(5)
$pythonExe = Join-Path $Dest 'data\apps\MC_L4\python\python.exe'
$stable = 0
$lastSize = -1
while ($stable -lt 3) {
    if ((Get-Date) -gt $installDeadline) {
        throw "Installer did not finish writing $pythonExe"
    }
    if ((Test-Path (Join-Path $Dest 'MC_L4.exe')) -and (Test-Path $pythonExe)) {
        $size = (Get-Item $pythonExe).Length
        if ($size -gt 0 -and $size -eq $lastSize) { $stable++ } else { $stable = 0; $lastSize = $size }
    } else {
        $stable = 0
    }
    Start-Sleep -Seconds 2
}
Write-Host "python.exe size=$lastSize"
New-Item -ItemType Directory -Force -Path $Evidence | Out-Null

$kept = Join-Path $Dest 'data\config\user-kept.txt'
New-Item -ItemType Directory -Force -Path (Split-Path $kept) | Out-Null
Set-Content -LiteralPath $kept -Value 'keep-this-user-file' -Encoding utf8
$configPath = Join-Path $Dest 'data\apps\MC_L4\working\config.py'
$taskPath = Join-Path $Dest 'data\apps\MC_L4\working\src\task\BaseWWTask.py'
$configHash = (Get-FileHash -LiteralPath $configPath -Algorithm SHA256).Hash
$taskHash = (Get-FileHash -LiteralPath $taskPath -Algorithm SHA256).Hash
Write-Host "bundled config=$configHash task=$taskHash"

try {
    Invoke-LauncherScenario 'clean' $kept $configHash $taskHash

    $appJson = Join-Path $Dest 'data\apps\MC_L4\app.json'
    $stalePatch = Join-Path $env:TEMP 'mcl4-stale-app.py'
    @'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
app = json.loads(path.read_text(encoding="utf-8"))
app["available_versions"] = ["v3.7.19"]
app["current_version"] = None
app["current_profile"] = "Global"
app["update_state"] = "idle"
app["update_target_version"] = None
app["update_error"] = None
app["profiles"] = [
    {
        "name": "China",
        "main_script": "main.py",
        "admin": True,
        "use_pythonw": True,
        "show_add_defender": True,
        "requirements": "requirements.txt",
        "PYTHONPATH": "",
        "git_url": "https://cnb.cool/ok-oldking/ok-ww-update2.git",
        "requires_python": "3.12",
        "pip_args": "--no-deps",
    },
    {
        "name": "Global",
        "main_script": "main.py",
        "admin": True,
        "use_pythonw": True,
        "show_add_defender": True,
        "requirements": "requirements.txt",
        "PYTHONPATH": "",
        "git_url": "https://github.com/ok-oldking/ok-ww-update.git",
        "requires_python": "3.12",
        "pip_args": "--no-deps",
    },
]
path.write_text(json.dumps(app, indent=2), encoding="utf-8")
'@ | Set-Content -LiteralPath $stalePatch -Encoding utf8NoBOM
    python $stalePatch $appJson
    if ($LASTEXITCODE -ne 0) { throw 'Could not write the stale upgrade app.json' }
    Invoke-LauncherScenario 'upgrade' $kept $configHash $taskHash
} finally {
    Show-SmokeLogs
    Get-ChildItem $Evidence | Select-Object Name, Length | Format-Table -AutoSize | Out-String | Write-Host
}
