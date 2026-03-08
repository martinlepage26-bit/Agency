param()

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Launcher = Join-Path $ProjectDir "launch_agency_lotus.vbs"
$IconPath = Join-Path $ProjectDir "agency_lotus_icon.ico"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutNames = @(
    "Agency LOTUS.lnk",
    "Dr. Sort-Academic Helper.lnk"
)

$Shell = New-Object -ComObject WScript.Shell
foreach ($ShortcutName in $ShortcutNames) {
    $ShortcutPath = Join-Path $Desktop $ShortcutName
    $Shortcut = $Shell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = Join-Path $env:SystemRoot "System32\wscript.exe"
    $Shortcut.Arguments = '"' + $Launcher + '"'
    $Shortcut.WorkingDirectory = $ProjectDir
    $Shortcut.Description = "Launch Agency LOTUS - Dr. Sort-Academic Helper"
    if (Test-Path $IconPath) {
        $Shortcut.IconLocation = $IconPath
    }
    else {
        $Shortcut.IconLocation = Join-Path $env:SystemRoot "System32\shell32.dll,220"
    }
    $Shortcut.Save()
}

Get-ChildItem $Desktop -Filter "*.lnk" |
    Where-Object { $_.Name -in $ShortcutNames } |
    Select-Object Name, FullName
