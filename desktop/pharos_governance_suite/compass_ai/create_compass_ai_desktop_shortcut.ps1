param()

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$IconPath = Join-Path $ProjectDir "compass_ai_icon.ico"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "CompassAI.lnk"

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = Join-Path $env:SystemRoot "System32\wscript.exe"
$Shortcut.Arguments = '"' + (Join-Path $ProjectDir "launch_compass_ai.vbs") + '"'
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.Description = "Launch CompassAI desktop intake and risk tier app"
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = $IconPath
}
else {
    $Shortcut.IconLocation = Join-Path $env:SystemRoot "System32\shell32.dll,137"
}
$Shortcut.Save()

Get-Item $ShortcutPath | Select-Object Name, FullName
