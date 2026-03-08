param()

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$IconPath = Join-Path $ProjectDir "lotus_icon.ico"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutMap = @(
    @{
        Name = "LOTUS.lnk"
        Launcher = Join-Path $ProjectDir "launch_lotus.vbs"
        Description = "Launch LOTUS score app"
    },
    @{
        Name = "Dr. Sort-Academic Helper.lnk"
        Launcher = Join-Path $ProjectDir "launch_dr_sort.vbs"
        Description = "Launch Dr. Sort-Academic Helper"
    }
)
$ShortcutNames = $ShortcutMap | ForEach-Object { $_.Name }
$LegacyShortcutNames = @("Agency LOTUS.lnk")

foreach ($LegacyName in $LegacyShortcutNames) {
    $LegacyPath = Join-Path $Desktop $LegacyName
    if (Test-Path $LegacyPath) {
        Remove-Item $LegacyPath -Force
    }
}

$Shell = New-Object -ComObject WScript.Shell
foreach ($ShortcutSpec in $ShortcutMap) {
    $ShortcutPath = Join-Path $Desktop $ShortcutSpec.Name
    $Shortcut = $Shell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = Join-Path $env:SystemRoot "System32\wscript.exe"
    $Shortcut.Arguments = '"' + $ShortcutSpec.Launcher + '"'
    $Shortcut.WorkingDirectory = $ProjectDir
    $Shortcut.Description = $ShortcutSpec.Description
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
