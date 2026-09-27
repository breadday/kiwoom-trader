# Git history rewrite — STEP 07F safety record

## Purpose and authorization

The repository history contained an account-like hard-coded portfolio snapshot in `kiwoom_rescue_bot.py`. The user explicitly changed the prior preservation decision and authorized rewriting the affected Git history and force-pushing the affected refs. Verbatim authorization: “이전 결정을 바꿔 과거 자료 제거를 위한 Git 이력 재작성과 force-push를 명시 승인합니다.” The current publication/integration request is: “지금까지 작업한거 모두 반영하고 push 하고 합치자 그리고 다른 ai 한데 작업 시킬게. 앞으로 작업 할 내용 md 로 정리해줘 그리고 push 해 주면 다운 받아서 다음 이어 개발할게”. No financial values or account-like positions are reproduced here.

## Rewrite method and local verification

A fresh mirror of `breadday/kiwoom-trader` was filtered with `git-filter-repo --path kiwoom_rescue_bot.py --invert-paths`. Each of the six rewritten branch refs was checked with `git rev-list --objects <ref>` and has no reachable object path named `kiwoom_rescue_bot.py`. The previous `main`/STEP 07 tip `87cbe121ca5aa6e5af7764997165dca920f67aa8` and previous STEP 07E tip `8986873e5f454c9a23424fadc7669d8f4074d46d` both return exit 128 from `git cat-file -e <sha>^{commit}` in the filtered mirror object database. The sanitized offline demo is committed locally on STEP 07F source commit `7924a48f2d9b2bf1506f51a383f203382a331d8f`; the reviewed documentation handoff was committed and fast-forwarded into local rewritten `main`. GitHub still advertises the pre-rewrite refs until a guarded remote push and readback succeed.

The original Windows checkout and other clones have not been modified. A Docker HTTPS dry-run failed because the container could not read an interactive username; SSH authentication is not configured. The last public GitHub snapshot had the six old branch refs in the table and no advertised tags. Locally, the reviewed STEP 07F/handoff HEAD was fast-forward integrated into rewritten `main`; no remote write has occurred. Any status-only documentation commit changes that local HEAD, so regenerate the bundle and pinned PowerShell script from the exact final local SHA before use. Required safeguards remain exact old-ref snapshot comparison, a single atomic `--force-with-lease` push for the seven intended refs, an empty lease for new STEP 07F, and exact post-push ref→SHA readback.

## Existing remote branch mapping (filtered base before final STEP 07F integration)

| Remote branch | Before rewrite | Rewritten head |
|---|---|---|
| `main` | `87cbe121ca5aa6e5af7764997165dca920f67aa8` | `b54e785bc1c9d65f1d034ae6d3f55b1ae199c4c1` |
| `feat/kiwoom-daily-backtest-stage-07` | `87cbe121ca5aa6e5af7764997165dca920f67aa8` | `b54e785bc1c9d65f1d034ae6d3f55b1ae199c4c1` |
| `feat/kiwoom-daily-backtest-stage-07b` | `fd71b57c71f9db57ab91a8f4f3a82360a58d6a8e` | `6966a33daeb91bdb6dca5bc265f6a8038d5548bf` |
| `feat/kiwoom-daily-backtest-stage-07c` | `a42a34d17cf3fb8e962cd9aaba4b2d6406e40176` | `56c8b8efc5568411b29c95402721428a9d658089` |
| `feat/kiwoom-daily-chart-contract-stage-07d` | `e1b60292add4ccd635d7c49d9e4d6e63ca7e49d5` | `5f888320fa31ac1eff7eb54e91f150e9560cd106` |
| `feat/kiwoom-auth-token-log-safety-stage-07e` | `8986873e5f454c9a23424fadc7669d8f4074d46d` | `8219afc718936e56c1a8ba5adad998f33f848248` |

## Expected final advertised refs

After final STEP 07F handoff commit is reviewed, `refs/heads/main` and `refs/heads/feat/kiwoom-rescue-demo-data-sanitization-stage-07f` must both equal that exact commit SHA, captured with `git rev-parse` immediately before push. The other five branch targets stay at the filtered heads in the table above: STEP 07 at `b54e785bc1c9d65f1d034ae6d3f55b1ae199c4c1`, STEP 07B at `6966a33daeb91bdb6dca5bc265f6a8038d5548bf`, STEP 07C at `56c8b8efc5568411b29c95402721428a9d658089`, STEP 07D at `5f888320fa31ac1eff7eb54e91f150e9560cd106`, and STEP 07E at `8219afc718936e56c1a8ba5adad998f33f848248`. The expected branch set is exactly those seven refs (main, STEP 07, 07B, 07C, 07D, 07E, 07F). Expected tags: none, as observed on 2026-09-27; stop if any tag or unexpected branch appears. The old SHA snapshot for the six existing refs must still match the table's “Before rewrite” values immediately before the atomic write; the new STEP 07F ref must be absent before push.

The rewrite also changes commit IDs referenced in older stage notes. Those notes describe the successful state at the time; this table is the post-rewrite ref mapping.

## Safety limits and follow-up

- The sanitized offline replacement is committed on the local STEP 07F branch. For release, fast-forward rewritten `main` to the final reviewed STEP 07F/handoff HEAD so `main` and the new STEP 07F branch advertise the same commit. GitHub publication remains pending until the atomic lease-protected push succeeds and all refs are read back.
- Force-pushing branch refs does not erase copies in existing clones, forks, backups, GitHub caches, or unadvertised server-side refs. Use a fresh clone after the rewrite; do not push from an old clone. For server-side cached/unreachable object removal, GitHub support may be required.
- The push script must not disable branch protection. If GitHub rejects force updates, stop and resolve repository policy deliberately; do not fall back to `--force` or `--mirror`.
- No account, credential, market-data, or order API was used.
