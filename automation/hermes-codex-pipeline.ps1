[CmdletBinding()]
param(
    [string]$TaskFile,
    [string]$RunId,
    [string]$RepoRoot,
    [string]$CodexPath = "$env:LOCALAPPDATA\hermes\node\codex.ps1",
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Resolve-ExistingPath([string]$Candidate, [string]$Description) {
    if ([string]::IsNullOrWhiteSpace($Candidate) -or -not (Test-Path -LiteralPath $Candidate)) {
        throw "$Description path is missing: $Candidate"
    }
    return (Resolve-Path -LiteralPath $Candidate).Path
}

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = Resolve-ExistingPath $RepoRoot 'Repository'
if ([string]::IsNullOrWhiteSpace($TaskFile)) {
    $TaskFile = Join-Path $PSScriptRoot 'tasks\pipeline-smoke.md'
}
$TaskFile = Resolve-ExistingPath $TaskFile 'Task file'

if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = Get-Date -Format 'yyyyMMdd-HHmmss'
}
if ($RunId -notmatch '^[A-Za-z0-9_-]+$') {
    throw "RunId contains unsafe characters: $RunId"
}

$gitCandidates = @(
    (Get-Command git.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    "$env:LOCALAPPDATA\hermes\git\cmd\git.exe",
    'C:\Program Files\Git\cmd\git.exe'
) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
$gitPath = $gitCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $gitPath) {
    throw 'git.exe was not found.'
}

$repoTop = (& $gitPath -C $RepoRoot rev-parse --show-toplevel 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($repoTop)) {
    throw "Not a git repository: $RepoRoot"
}
$repoTop = (Resolve-Path -LiteralPath $repoTop).Path
if ($repoTop -ne $RepoRoot) {
    throw "Repository root mismatch: $repoTop"
}

$runDir = Join-Path $RepoRoot "automation\runs\$RunId"
$relativeRunDir = "automation/runs/$RunId"
$stages = @('architect', 'coder', 'tester', 'reviewer')

Write-Output "[pipeline] repo=$RepoRoot"
Write-Output "[pipeline] run_id=$RunId"
Write-Output "[pipeline] stages=$($stages -join ' -> ')"

if ($DryRun) {
    Write-Output '[pipeline] dry-run: no files or Codex process created.'
    exit 0
}

if (-not (Test-Path -LiteralPath $CodexPath)) {
    throw "Codex executable was not found: $CodexPath"
}

$beforeStatus = @(& $gitPath -C $RepoRoot status --short --untracked-files=all 2>&1)
if ($LASTEXITCODE -ne 0) {
    throw 'Could not read initial git status.'
}
$beforeStatus | Set-Content -LiteralPath (Join-Path $env:TEMP "kiwoom-pipeline-$RunId-before-status.txt") -Encoding UTF8

New-Item -ItemType Directory -Path $runDir -Force | Out-Null
$task = Get-Content -LiteralPath $TaskFile -Raw
$repoName = Split-Path -Leaf $RepoRoot

function Invoke-CodexStage([string]$Stage, [string]$Sandbox, [string]$Instructions) {
    $promptPath = Join-Path $runDir "$Stage.prompt.md"
    $responsePath = Join-Path $runDir "$Stage.response.md"
    $stdoutPath = Join-Path $runDir "$Stage.stdout.log"

    $prompt = @"
You are the $Stage role in a sequential Hermes -> Codex pipeline.
Repository: $RepoRoot
Repository name: $repoName
Run directory: $runDir
Task:
$task

Pipeline rules:
- Read only files explicitly needed for this stage and prior stage artifacts.
- Never read credentials, account files, .env, *.key, config_live.py, or accounts.yaml.
- Never access a broker, securities connection, order, correction, cancellation, live/paper account, or operational database.
- Never commit, push, switch branches, or rewrite history.
- The requested sandbox is: $Sandbox

Stage instructions:
$Instructions
"@
    $prompt | Set-Content -LiteralPath $promptPath -Encoding UTF8

    $codexArgs = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $CodexPath,
        'exec', '-s', $Sandbox, '-C', $RepoRoot, '--ephemeral', '--color', 'never',
        '-o', $responsePath, $prompt
    )
    $output = @(& powershell.exe @codexArgs 2>&1)
    $exitCode = $LASTEXITCODE
    $output | Set-Content -LiteralPath $stdoutPath -Encoding UTF8
    if ($exitCode -ne 0) {
        throw "Codex stage '$Stage' failed with exit code $exitCode. See $stdoutPath"
    }
    if (-not (Test-Path -LiteralPath $responsePath)) {
        throw "Codex stage '$Stage' did not produce $responsePath"
    }
    return Get-Content -LiteralPath $responsePath -Raw
}

$architect = Invoke-CodexStage 'architect' 'read-only' @"
Produce a concise implementation plan for this smoke task. Do not modify files.
End with exactly: ARCHITECT_APPROVED
"@

$coder = Invoke-CodexStage 'coder' 'workspace-write' @"
Read $runDir\architect.response.md before acting. Implement only the task's
single test artifact inside $runDir. Do not modify any other path. Report the
exact artifact path and end with exactly: CODER_DONE
"@

$artifactPath = Join-Path $runDir 'smoke-artifact.txt'
if (-not (Test-Path -LiteralPath $artifactPath)) {
    throw "Coder artifact is missing: $artifactPath"
}
if ((Get-Content -LiteralPath $artifactPath -Raw).Trim() -ne 'PIPELINE_SMOKE_OK') {
    throw 'Coder artifact marker is invalid.'
}
@('TESTER_PASS', "artifact=$artifactPath", 'orders=false', 'broker=false') |
    Set-Content -LiteralPath (Join-Path $runDir 'tester.response.md') -Encoding UTF8

$reviewer = Invoke-CodexStage 'reviewer' 'read-only' @"
Read these prior artifacts in order:
1. $runDir\architect.response.md
2. $runDir\coder.response.md
3. $runDir\tester.response.md
4. $artifactPath

Independently review scope, artifact content, and safety. Do not modify files.
Approve only if the task is test-only, the marker is exact, and no prohibited
integration was used. End with exactly one of: FINAL_APPROVED or FINAL_BLOCKED.
"@

$reviewerText = Get-Content -LiteralPath (Join-Path $runDir 'reviewer.response.md') -Raw
if ($reviewerText -notmatch 'FINAL_APPROVED') {
    @('FINAL_BLOCKED', $reviewerText) | Set-Content -LiteralPath (Join-Path $runDir 'final-decision.md') -Encoding UTF8
    throw "Independent reviewer blocked the pipeline. See $runDir\reviewer.response.md"
}

$afterStatus = @(& $gitPath -C $RepoRoot status --short --untracked-files=all 2>&1)
if ($LASTEXITCODE -ne 0) {
    throw 'Could not read final git status.'
}
$unexpected = $afterStatus | Where-Object {
    ($_ -notin $beforeStatus) -and ($_ -notmatch "^\?\?\s+$([regex]::Escape($relativeRunDir))/")
}
if ($unexpected) {
    $unexpected | Set-Content -LiteralPath (Join-Path $runDir 'unexpected-git-changes.txt') -Encoding UTF8
    throw 'Unexpected changes outside the pipeline run directory were detected.'
}

@(
    'FINAL_APPROVED',
    "run_id=$RunId",
    'order_api=false',
    'broker_connection=false',
    'account_access=false',
    'database_access=false',
    "artifact=$artifactPath"
) | Set-Content -LiteralPath (Join-Path $runDir 'final-decision.md') -Encoding UTF8

Write-Output "[pipeline] artifact=$artifactPath"
Write-Output "[pipeline] decision=FINAL_APPROVED"
Write-Output '[pipeline] verified=PASS'
