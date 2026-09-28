# 자동 개발 STEP 08E — read-only market-data 검증 테스트

## 안전 경계

- 실제 계좌·잔고·주문·정정·취소 endpoint를 호출하지 않는다.
- credential 파일(`accounts.yaml`, `config_live.py`, `.env`, `*.key`, `token.json`)을 읽지 않는다.
- 승인 전에는 실제 Kiwoom network endpoint를 호출하지 않는다.
- fixture와 fake response는 이미 08A~08D 회귀 테스트에서 검증한다.

## 로컬 사전 검증

```powershell
$env:PYTHONPATH=(Resolve-Path .tmp-pydeps).Path
python -m unittest discover -s tests -p 'test_*.py' -q
python -m compileall -q api tests
git diff --check
```

기대 결과: unittest 76개 `OK`, compileall exit 0, diff-check exit 0.

## 실제 smoke test 실행 조건

실제 실행은 위 선행 조건이 충족된 별도 승인 환경에서만 수행한다. 테스트
호출은 하나의 명시된 종목과 기준일에 제한하고, 반환된 OHLCV를 화면에
출력하되 token·header·account field는 출력하거나 저장하지 않는다.

현재 저장소에서는 안전한 credential 주입 경로와 승인된 Kiwoom 네트워크
환경이 확인되지 않았으므로 실제 smoke test를 실행하지 않는다.
