# Hermes → Codex 오케스트레이션

저장소 로컬 진입점은 `hermes-codex.ps1`다. Hermes에서 작업을 위임하면 이
스크립트가 저장소 루트, Codex 샌드박스 정책, 전후 Git 상태를 고정한다.

## 안전한 smoke 검증

```powershell
.\hermes-codex.ps1 -Mode smoke
```

smoke/inspect/verify는 Codex `read-only`로 실행되며, 전후 Git 상태가 바뀌면
실패한다. 구현을 요청할 때만 다음처럼 명시적으로 `workspace-write`를 켠다.

```powershell
.\hermes-codex.ps1 -Mode implement -TaskFile .\tasks\my-task.md
```

실계좌·실주문·credential 접근은 이 오케스트레이션의 범위가 아니다. 커밋과
푸시는 자동 실행하지 않는다.

## 안전한 자동 연속 진행

`continue_safe.py`는 외부 서비스·credential·주문·commit/push 없이 로컬 개발 상태를 반복 검증하고 결과를 `docs/AUTOMATED-CONTINUATION-RESULTS.md`에 기록한다.

```powershell
.\.venv\Scripts\python.exe automation\continue_safe.py
```

계획·개발·테스트·검증 문서는 다음에 있다.

- `docs/AUTOMATED-CONTINUATION-PLAN.md`
- `docs/AUTOMATED-CONTINUATION-DEVELOPMENT.md`
- `docs/AUTOMATED-CONTINUATION-TEST.md`
- `docs/AUTOMATED-CONTINUATION-VERIFICATION.md`
- 미처리 외부 게이트: `docs/UNRESOLVED.md`


`hermes-codex-pipeline.ps1`는 Architect → Coder → Tester → Reviewer 순서로
실행한다. 각 단계의 prompt/response/log와 최종 판정을
`automation/runs/<run-id>/`에 남긴다. Coder가 만들 수 있는 것은 smoke
작업의 테스트 전용 artifact 하나뿐이며, Reviewer가 `FINAL_APPROVED`를
반환하고 기존 Git 변경이 보존될 때만 성공한다.

```powershell
.\hermes-codex-pipeline.ps1
```

실행 전 구조만 확인하려면 `-DryRun`을 사용한다. 자동 병합과 push는 없다.
