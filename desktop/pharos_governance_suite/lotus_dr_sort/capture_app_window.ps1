param(
    [Parameter(Mandatory = $true)]
    [string]$CommandPath,

    [string[]]$Arguments = @(),

    [Parameter(Mandatory = $true)]
    [string]$WindowTitle,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath,

    [int]$TimeoutSeconds = 25,

    [int]$InitialDelayMs = 1500,

    [int]$ForegroundDelayMs = 900
)

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

Add-Type @"
using System;
using System.Runtime.InteropServices;

public struct RECT {
    public int Left;
    public int Top;
    public int Right;
    public int Bottom;
}

public static class Win32Capture {
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
}
"@

$scriptDir = Split-Path -Parent $PSCommandPath
$process = $null
$windowProcess = $null

try {
    $process = Start-Process -FilePath $CommandPath -ArgumentList $Arguments -PassThru -WorkingDirectory $scriptDir
    Start-Sleep -Milliseconds $InitialDelayMs

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $windowProcess = Get-Process | Where-Object {
            $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -eq $WindowTitle
        } | Select-Object -First 1

        if ($windowProcess) {
            break
        }

        Start-Sleep -Milliseconds 350
    }

    if (-not $windowProcess) {
        throw "Window '$WindowTitle' was not found within $TimeoutSeconds seconds."
    }

    [Win32Capture]::ShowWindowAsync($windowProcess.MainWindowHandle, 5) | Out-Null
    [Win32Capture]::SetForegroundWindow($windowProcess.MainWindowHandle) | Out-Null
    Start-Sleep -Milliseconds $ForegroundDelayMs

    $rect = New-Object RECT
    if (-not [Win32Capture]::GetWindowRect($windowProcess.MainWindowHandle, [ref]$rect)) {
        throw "Failed to read the window bounds for '$WindowTitle'."
    }

    $width = [Math]::Max(1, $rect.Right - $rect.Left)
    $height = [Math]::Max(1, $rect.Bottom - $rect.Top)
    $bitmap = New-Object System.Drawing.Bitmap $width, $height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)

    try {
        $graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bitmap.Size)
        $parent = Split-Path -Parent $OutputPath
        if ($parent) {
            New-Item -ItemType Directory -Force -Path $parent | Out-Null
        }
        $bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
        Write-Output "Saved screenshot to $OutputPath"
    }
    finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}
finally {
    if ($windowProcess) {
        $windowProcess.CloseMainWindow() | Out-Null
        Start-Sleep -Milliseconds 500
        if (-not $windowProcess.HasExited) {
            $windowProcess.Kill()
        }
    }
    elseif ($process) {
        $process.CloseMainWindow() | Out-Null
        Start-Sleep -Milliseconds 500
        if (-not $process.HasExited) {
            $process.Kill()
        }
    }
}
