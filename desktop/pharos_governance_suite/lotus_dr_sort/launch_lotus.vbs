Option Explicit

Dim shell, fso, appRoot, launcher
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

appRoot = fso.GetParentFolderName(WScript.ScriptFullName)
launcher = fso.BuildPath(appRoot, "LOTUS.bat")

shell.CurrentDirectory = appRoot
shell.Run Chr(34) & launcher & Chr(34), 0, False

Set fso = Nothing
Set shell = Nothing
