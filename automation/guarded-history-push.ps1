[CmdletBinding()]
param(
    [string]$Remote = 'origin',
    [switch]$Execute,
    [switch]$ConfirmRewrite
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if ($Execute -and -not $ConfirmRewrite) {
    throw '실제 history rewrite push에는 -Execute -ConfirmRewrite가 모두 필요합니다.'
}

$repoRoot = (git rev-parse --show-toplevel 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($repoRoot)) {
    throw 'Git 저장소 루트에서 실행해야 합니다.'
}
Set-Location -LiteralPath $repoRoot

$expectedOld = [ordered]@{
    'refs/heads/main' = '87cbe121ca5aa6e5af7764997165dca920f67aa8'
    'refs/heads/feat/kiwoom-daily-backtest-stage-07' = '87cbe121ca5aa6e5af7764997165dca920f67aa8'
    'refs/heads/feat/kiwoom-daily-backtest-stage-07b' = 'fd71b57c71f9db57ab91a8f4f3a82360a58d6a8e'
    'refs/heads/feat/kiwoom-daily-backtest-stage-07c' = 'a42a34d17cf3fb8e962cd9aaba4b2d6406e40176'
    'refs/heads/feat/kiwoom-daily-chart-contract-stage-07d' = 'e1b60292add4ccd635d7c49d9e4d6e63ca7e49d5'
    'refs/heads/feat/kiwoom-auth-token-log-safety-stage-07e' = '8986873e5f454c9a23424fadc7669d8f4074d46d'
}

$expectedNew = [ordered]@{
    'refs/heads/feat/kiwoom-daily-backtest-stage-07' = 'b54e785bc1c9d65f1d034ae6d3f55b1ae199c4c1'
    'refs/heads/feat/kiwoom-daily-backtest-stage-07b' = '6966a33daeb91bdb6dca5bc265f6a8038d5548bf'
    'refs/heads/feat/kiwoom-daily-backtest-stage-07c' = '56c8b8efc5568411b29c95402721428a9d658089'
    'refs/heads/feat/kiwoom-daily-chart-contract-stage-07d' = '5f888320fa31ac1eff7eb54e91f150e9560cd106'
    'refs/heads/feat/kiwoom-auth-token-log-safety-stage-07e' = '8219afc718936e56c1a8ba5adad998f33f848248'
}

$finalSha = (git rev-parse HEAD 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $finalSha -notmatch '^[0-9a-f]{40}$') {
    throw '현재 HEAD SHA를 확인할 수 없습니다.'
}

$status = @(git status --short --untracked-files=all)
if ($status.Count -ne 0) {
    throw "작업 트리가 clean하지 않습니다: $($status -join '; ')"
}

foreach ($sha in $expectedNew.Values) {
    git cat-file -e "$sha^{commit}" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "로컬에 expected rewritten commit이 없습니다: $sha"
    }
}

$heads = @(git ls-remote --heads $Remote)
if ($LASTEXITCODE -ne 0) {
    throw '원격 heads를 읽지 못했습니다. 네트워크와 인증을 확인한 뒤 재시도하십시오.'
}
$tags = @(git ls-remote --tags --refs $Remote)
if ($LASTEXITCODE -ne 0) {
    throw '원격 tags를 읽지 못했습니다. 원격 write를 수행하지 않습니다.'
}

$remoteRefs = [ordered]@{}
foreach ($line in $heads) {
    if ($line -match '^([0-9a-f]{40})\s+(refs/heads/.+)$') {
        $remoteRefs[$Matches[2]] = $Matches[1]
    }
}
$expectedOld.Keys | ForEach-Object {
    if (-not $remoteRefs.Contains($_) -or $remoteRefs[$_] -ne $expectedOld[$_]) {
        throw "old snapshot 불일치: $_ expected=$($expectedOld[$_]) actual=$($remoteRefs[$_])"
    }
}
$unexpected = @($remoteRefs.Keys | Where-Object { $_ -notin $expectedOld.Keys })
if ($unexpected.Count -ne 0) {
    throw "예상하지 않은 remote branch가 있습니다: $($unexpected -join ', ')"
}
if ($tags.Count -ne 0) {
    throw '예상하지 않은 remote tag가 있어 중단합니다.'
}

$historyTargets = @(
    'b54e785bc1c9d65f1d034ae6d3f55b1ae199c4c1',
    '6966a33daeb91bdb6dca5bc265f6a8038d5548bf',
    '56c8b8efc5568411b29c95402721428a9d658089',
    '5f888320fa31ac1eff7eb54e91f150e9560cd106',
    '8219afc718936e56c1a8ba5adad998f33f848248'
)
foreach ($sha in $historyTargets) {
    $pathMatch = @(git rev-list --objects $sha | Where-Object { $_ -match '\s+kiwoom_rescue_bot\.py$' })
    if ($pathMatch.Count -ne 0) {
        throw "정화 대상 branch에 금지 경로가 남아 있습니다: $sha"
    }
}

$newRef = 'refs/heads/feat/kiwoom-rescue-demo-data-sanitization-stage-07f'
if ($remoteRefs.Contains($newRef)) {
    throw "새 STEP 07F ref가 이미 원격에 존재합니다. empty lease 조건을 적용하지 않습니다."
}

Write-Output "preflight=PASS"
Write-Output "final_sha=$finalSha"
Write-Output 'remote_old_snapshot=PASS'
Write-Output 'remote_tags=EMPTY'
Write-Output 'history_path_scan=PASS'
Write-Output 'step07f_absent=PASS'

if (-not $Execute) {
    Write-Output 'mode=DRY_RUN'
    Write-Output 'next=run with -Execute -ConfirmRewrite only after reviewing this output'
    exit 0
}

$pushSpecs = @(
    "${finalSha}:refs/heads/main",
    "${expectedNew['refs/heads/feat/kiwoom-daily-backtest-stage-07']}:refs/heads/feat/kiwoom-daily-backtest-stage-07",
    "${expectedNew['refs/heads/feat/kiwoom-daily-backtest-stage-07b']}:refs/heads/feat/kiwoom-daily-backtest-stage-07b",
    "${expectedNew['refs/heads/feat/kiwoom-daily-backtest-stage-07c']}:refs/heads/feat/kiwoom-daily-backtest-stage-07c",
    "${expectedNew['refs/heads/feat/kiwoom-daily-chart-contract-stage-07d']}:refs/heads/feat/kiwoom-daily-chart-contract-stage-07d",
    "${expectedNew['refs/heads/feat/kiwoom-auth-token-log-safety-stage-07e']}:refs/heads/feat/kiwoom-auth-token-log-safety-stage-07e",
    "${finalSha}:refs/heads/feat/kiwoom-rescue-demo-data-sanitization-stage-07f"
)
$leases = @(
    '--force-with-lease=refs/heads/main:' + $expectedOld['refs/heads/main'],
    '--force-with-lease=refs/heads/feat/kiwoom-daily-backtest-stage-07:' + $expectedOld['refs/heads/feat/kiwoom-daily-backtest-stage-07'],
    '--force-with-lease=refs/heads/feat/kiwoom-daily-backtest-stage-07b:' + $expectedOld['refs/heads/feat/kiwoom-daily-backtest-stage-07b'],
    '--force-with-lease=refs/heads/feat/kiwoom-daily-backtest-stage-07c:' + $expectedOld['refs/heads/feat/kiwoom-daily-backtest-stage-07c'],
    '--force-with-lease=refs/heads/feat/kiwoom-daily-chart-contract-stage-07d:' + $expectedOld['refs/heads/feat/kiwoom-daily-chart-contract-stage-07d'],
    '--force-with-lease=refs/heads/feat/kiwoom-auth-token-log-safety-stage-07e:' + $expectedOld['refs/heads/feat/kiwoom-auth-token-log-safety-stage-07e'],
    '--force-with-lease=refs/heads/feat/kiwoom-rescue-demo-data-sanitization-stage-07f:'
)

git push $Remote @leases @pushSpecs
if ($LASTEXITCODE -ne 0) {
    throw 'atomic force-with-lease push가 실패했습니다.'
}

$afterHeads = @(git ls-remote --heads $Remote)
$afterTags = @(git ls-remote --tags --refs $Remote)
if ($LASTEXITCODE -ne 0 -or $afterTags.Count -ne 0) {
    throw 'push 후 원격 readback 또는 tag 검증에 실패했습니다.'
}
$expectedAfter = [ordered]@{
    'refs/heads/main' = $finalSha
    'refs/heads/feat/kiwoom-daily-backtest-stage-07' = $expectedNew['refs/heads/feat/kiwoom-daily-backtest-stage-07']
    'refs/heads/feat/kiwoom-daily-backtest-stage-07b' = $expectedNew['refs/heads/feat/kiwoom-daily-backtest-stage-07b']
    'refs/heads/feat/kiwoom-daily-backtest-stage-07c' = $expectedNew['refs/heads/feat/kiwoom-daily-backtest-stage-07c']
    'refs/heads/feat/kiwoom-daily-chart-contract-stage-07d' = $expectedNew['refs/heads/feat/kiwoom-daily-chart-contract-stage-07d']
    'refs/heads/feat/kiwoom-auth-token-log-safety-stage-07e' = $expectedNew['refs/heads/feat/kiwoom-auth-token-log-safety-stage-07e']
    $newRef = $finalSha
}
$actualAfter = [ordered]@{}
foreach ($line in $afterHeads) {
    if ($line -match '^([0-9a-f]{40})\s+(refs/heads/.+)$') {
        $actualAfter[$Matches[2]] = $Matches[1]
    }
}
if ($actualAfter.Count -ne $expectedAfter.Count) {
    throw 'push 후 branch 수가 expected set과 다릅니다.'
}
foreach ($ref in $expectedAfter.Keys) {
    if (-not $actualAfter.Contains($ref) -or $actualAfter[$ref] -ne $expectedAfter[$ref]) {
        throw "push 후 SHA 불일치: $ref expected=$($expectedAfter[$ref]) actual=$($actualAfter[$ref])"
    }
}
Write-Output 'post_push_readback=PASS'
