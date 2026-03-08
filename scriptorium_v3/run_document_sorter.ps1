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

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ScriptPath = Join-Path $Root "document_sorter.py"
$LocalPython = Join-Path $Root ".venv\Scripts\python.exe"

if (Test-Path $LocalPython) {
    $PythonCmd = $LocalPython
}
elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
}
else {
    $PythonCmd = "python"
}

$Args = @(
    $ScriptPath,
    "--mode", $Mode,
    "--ocr", $Ocr,
    "--max-pages", "$MaxPages",
    "--output-root", (Join-Path $Root "SORTED_LIBRARY_V2"),
    "--quarantine-root", (Join-Path $Root "QUARANTINE\V2"),
    "--report-root", (Join-Path $Root "REPORTS_V2")
)

foreach ($Item in $Source) {
    if ($Item) {
        $Args += @("--source", $Item)
    }
}

if ($RulesFile) {
    $Args += @("--rules-file", $RulesFile)
}

if ($NoSimilarDedupe) {
    $Args += "--no-similar-dedupe"
}

if ($RenderCrossReference) {
    $Args += "--render-crossref"
}

if ($RenderMasterlist) {
    $Args += "--render-masterlist"
}

if ($NoRecursive) {
    $Args += "--no-recursive"
}

& $PythonCmd @Args
exit $LASTEXITCODE
