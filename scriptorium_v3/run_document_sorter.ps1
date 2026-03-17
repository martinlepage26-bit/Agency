param(
    [string[]]$Source,
    [ValidateSet("scan", "copy", "move")]
    [string]$Mode = "scan",
    [ValidateSet("auto", "never")]
    [string]$Ocr = "auto",
    [int]$MaxPages = 5,
    [string]$RulesFile,
    [switch]$RenderCrossReference,
    [switch]$RenderMasterlist,
    [switch]$NoSimilarDedupe,
    [switch]$NoRecursive
)

$DelegateScript = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\scripto\run_document_sorter.ps1"

if (-not (Test-Path $DelegateScript)) {
    throw "Could not find delegated Scripto runner at $DelegateScript"
}

& $DelegateScript `
    -Source $Source `
    -Mode $Mode `
    -Ocr $Ocr `
    -MaxPages $MaxPages `
    -RulesFile $RulesFile `
    -RenderCrossReference:$RenderCrossReference `
    -RenderMasterlist:$RenderMasterlist `
    -NoSimilarDedupe:$NoSimilarDedupe `
    -NoRecursive:$NoRecursive
exit $LASTEXITCODE
