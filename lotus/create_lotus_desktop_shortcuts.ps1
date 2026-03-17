param()

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$IconPath = Join-Path $ProjectDir "lotus_icon.ico"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "LOTUS.lnk"
$LegacyShortcutNames = @("Agency LOTUS.lnk")

foreach ($LegacyName in $LegacyShortcutNames) {
    $LegacyPath = Join-Path $Desktop $LegacyName
    if (Test-Path $LegacyPath) {
        Remove-Item $LegacyPath -Force
    }
}

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = Join-Path $env:SystemRoot "System32\wscript.exe"
$Shortcut.Arguments = '"' + (Join-Path $ProjectDir "launch_lotus.vbs") + '"'
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.Description = "Launch LOTUS"
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = $IconPath
}
else {
    $Shortcut.IconLocation = Join-Path $env:SystemRoot "System32\shell32.dll,220"
}
$Shortcut.Save()

Get-Item $ShortcutPath | Select-Object Name, FullName
