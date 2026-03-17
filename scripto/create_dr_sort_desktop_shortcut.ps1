param()

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "Dr. Sort-Academic Helper.lnk"

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = Join-Path $env:SystemRoot "System32\wscript.exe"
$Shortcut.Arguments = '"' + (Join-Path $ProjectDir "launch_dr_sort.vbs") + '"'
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.Description = "Launch Dr. Sort-Academic Helper"
$Shortcut.IconLocation = Join-Path $env:SystemRoot "System32\shell32.dll,220"
$Shortcut.Save()

Get-Item $ShortcutPath | Select-Object Name, FullName
