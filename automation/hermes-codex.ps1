[CmdletBinding()]
param(
    [ValidateSet('smoke', 'inspect', 'implement', 'verify')]
    [string]$Mode = 'smoke',

    [string]$TaskFile,

    [string]$RepoRoot,

    [string]$CodexPath = "$env:LOCALAPPDATA\hermes\node\codex.ps1",

    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Resolve-ExistingPath([string]$Candidate, [string]$Description) {
    if ([string]::IsNullOrWhiteSpace($Candidate)) {
        throw "$Description 경로가 비어 있습니다."
    }
    if (-not (Test-Path -LiteralPath $Candidate)) {
        throw "$Description 경로를 찾을 수 없습니다: $Candidate"
    }
    return (Resolve-Path -LiteralPath $Candidate).Path
}

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = Resolve-ExistingPath $RepoRoot '저장소'

$gitCandidates = @(
    (Get-Command git.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    "$env:LOCALAPPDATA\hermes\git\cmd\git.exe",
    'C:\Program Files\Git\cmd\git.exe'
) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
$gitPath = $gitCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $gitPath) {
    throw 'git.exe를 찾을 수 없습니다.'
}

$repoTop = (& $gitPath -C $RepoRoot rev-parse --show-toplevel 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($repoTop)) {
    throw "Git 저장소가 아닙니다: $RepoRoot"
}
$repoTop = (Resolve-Path -LiteralPath $repoTop).Path
if ($repoTop -ne $RepoRoot) {
    throw "저장소 루트와 실행 루트가 다릅니다: $repoTop"
}

$before = @(& $gitPath -C $RepoRoot status --short --untracked-files=all 2>&1)
if ($LASTEXITCODE -ne 0) {
    throw '작업 전 Git 상태 조회에 실패했습니다.'
}

if ([string]::IsNullOrWhiteSpace($TaskFile)) {
    $TaskFile = Join-Path $PSScriptRoot 'tasks\smoke.md'
}
$TaskFile = Resolve-ExistingPath $TaskFile '작업 파일'
$task = Get-Content -LiteralPath $TaskFile -Raw

$sandbox = if ($Mode -eq 'implement') { 'workspace-write' } else { 'read-only' }
$repoName = Split-Path -Leaf $RepoRoot
$safety = @"
저장소 루트는 정확히 다음 경로다: $RepoRoot
저장소 이름은 정확히 다음이다: $repoName
오케스트레이터 모드: $Mode
샌드박스 정책: $sandbox

안전 경계:
- 이 작업 파일의 범위를 벗어나지 않는다.
- 계좌, credential, token, .env, *.key, config_live.py, accounts.yaml을 읽지 않는다.
- 실계좌·paper/live 주문·주문 제출·브로커 쓰기 API를 호출하지 않는다.
- 모드가 implement가 아니면 파일을 생성·수정·삭제·이동하지 않는다.
- 테스트와 독립 리뷰 통과 후 현재 브랜치의 비강제 commit 및 push를 허용한다.
- force-push, 브랜치 삭제, 이력 재작성은 별도 명시 승인 없이는 금지한다.

작업 지시:
$task
"@

if (-not (Test-Path -LiteralPath $CodexPath)) {
    throw "Codex 실행 파일을 찾을 수 없습니다: $CodexPath"
}

$command = @(
    'powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $CodexPath,
    'exec', '-s', $sandbox, '-C', $RepoRoot, '--ephemeral', '--color', 'never', $safety
)

Write-Output "[hermes-codex] mode=$Mode repo=$RepoRoot sandbox=$sandbox"
Write-Output "[hermes-codex] before_status_count=$($before.Count)"

if ($DryRun) {
    Write-Output '[hermes-codex] dry-run: Codex 실행을 생략했습니다.'
    exit 0
}

if ([string]::IsNullOrWhiteSpace($env:USERPROFILE)) {
    $env:USERPROFILE = [Environment]::GetFolderPath('UserProfile')
}
if ([string]::IsNullOrWhiteSpace($env:HOME)) {
    $env:HOME = $env:USERPROFILE
}
if ([string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
    $env:CODEX_HOME = Join-Path $env:USERPROFILE '.codex'
}

$codexOutput = @(& $command[0] $command[1..($command.Count - 1)] 2>&1)
$codexExitCode = $LASTEXITCODE
$codexOutput | ForEach-Object { Write-Output $_ }
if ($codexExitCode -ne 0) {
    throw "Codex 실행 실패(exit=$codexExitCode)."
}

$after = @(& $gitPath -C $RepoRoot status --short --untracked-files=all 2>&1)
if ($LASTEXITCODE -ne 0) {
    throw '작업 후 Git 상태 조회에 실패했습니다.'
}

if ($Mode -ne 'implement' -and (($before -join "`n") -ne ($after -join "`n"))) {
    throw '읽기 전용 모드에서 Git 상태가 변했습니다.'
}

if ($Mode -eq 'smoke') {
    $joined = $codexOutput -join "`n"
    if ($joined -notmatch 'CODEX_SMOKE_OK\s+kiwoom_trader') {
        throw 'Codex smoke marker가 응답에 없습니다.'
    }
}

Write-Output "[hermes-codex] after_status_count=$($after.Count)"
Write-Output '[hermes-codex] verified=PASS'
