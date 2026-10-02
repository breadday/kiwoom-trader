# 자동 연속 진행 계획

## 목적

저장소에서 외부 인증·승인 없이 완료할 수 있는 개발, 테스트, 검증을 반복 실행하고, 외부 작업은 `docs/UNRESOLVED.md`에 남긴다.

## 실행 순서

1. `automation/continue_safe.py`로 로컬 테스트·compile·오프라인 데모·whitespace를 실행한다.
2. 실패한 단계가 있으면 해당 failing test와 원인을 확인한다.
3. 코드 변경은 테스트 우선으로 수정하고 전체 검증을 다시 실행한다.
4. 결과를 `docs/AUTOMATED-CONTINUATION-RESULTS.md`에 기록한다.
5. 외부 인증·원격 ref·실데이터·운영 endpoint 작업은 실행하지 않고 `docs/UNRESOLVED.md`에 유지한다.
6. 사용자가 별도로 승인한 경우에만 GitHub/Vercel/Telegram 등 외부 상태 변경을 별도 절차로 진행한다.

## 자동화 명령

저장소 루트에서 다음을 실행한다.

```bash
python automation/continue_safe.py
```

Windows 프로젝트 환경에서는 `.venv/Scripts/python.exe`를 사용한다.

## 완료 기준

- 테스트와 compile이 통과한다.
- 합성 데이터 오프라인 데모가 실행된다.
- whitespace 검사가 통과한다.
- 결과 문서가 갱신된다.
- 처리하지 못한 외부 게이트와 재개 조건이 `docs/UNRESOLVED.md`에 남아 있다.
