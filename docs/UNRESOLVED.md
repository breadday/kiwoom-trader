# 진행 보류 및 외부 검증 항목

이 문서는 로컬에서 해결할 수 없거나 운영 승인이 필요한 항목을 기록한다.
해결 불가를 의미하지 않으며, 조건이 갖춰지면 이 문서의 재개 절차를 따라 진행한다.

## 1. Kiwoom read-only smoke test

- 상태: 모의투자 smoke 완료 / 운영 검증 보류
- 결과: `005930` 일봉 5개 행을 `https://mockapi.kiwoom.com`에서 조회 성공.
- 재현: `automation/kiwoom_readonly_smoke.py`
- 남은 이유: 운영(real) endpoint와 실계좌 인증은 안전 범위 밖이며 별도 승인 필요.
- 안전 범위: 일봉 조회(read-only)만 허용한다. 주문 API와 실계좌 잔고 조회는 실행하지 않는다.
- 재개 조건:
  1. 운영자가 승인한 paper/read-only 앱 키와 시크릿을 로컬 환경변수로 제공한다.
  2. 비밀값을 저장소 파일이나 로그에 기록하지 않는다.
  3. `docs/AUTOMATION-STEP-08E-PLAN.md`와 `docs/AUTOMATION-STEP-08E-TEST.md`의 smoke 절차를 따른다.
  4. 응답 계약, 페이지네이션, rate limit, 휴장일, 가격 부호를 기록하고 테스트 fixture로 고정한다.

## 2. Vercel production 배포

- 상태: 완료 / Telegram production credential mapping은 별도 보류
- 결과: deployment `dpl_E1ahxTWJDjHavnU7xhLhPAss5JwM`이 `READY` 상태로 production에 반영되었다.
- read-back: `https://kiwoom-trader.vercel.app/` 및 `/api/index.py`가 모두 `{"ok": true, "mode": "paper", "readonly": true}`를 반환했다.
- 현재 준비: Vercel production env 목록에는 `KIWOOM_APP_KEY`, `KIWOOM_APP_SECRET`, `KIWOOM_BASE_URL`만 확인된다. Telegram 변수명은 확인되지 않았다.
- 안전 범위: 현재 entrypoint는 paper-only이며 live 주문 전환을 허용하지 않는다.
- 재개 조건:
  1. 이 Vercel 프로젝트의 Production에 `TELEGRAM_BOT_TOKEN`과 `TELEGRAM_CHAT_ID`를 secret store로 등록한다(값은 채팅/로그/저장소에 남기지 않는다).
  2. 실제 MATCH와 ERROR를 각각 한 번 전송하고 Telegram 수신 여부를 operator가 확인한다.
  3. 전송 전후 `vercel env ls production`에서 이름만 read-back하고, 토큰 값은 출력하지 않는다.

## 3. Telegram 운영 전송

- 상태: 보류 / production env mapping 미확인
- 이유: 현재 연결된 Vercel 프로젝트의 Production env read-back에 `TELEGRAM_BOT_TOKEN`과 `TELEGRAM_CHAT_ID`가 없어서 실제 전송을 안전하게 시작할 수 없다. 로컬 프로세스에도 해당 환경변수가 없다.
- 완료된 안전 검증: fake transport 기반 Telegram 테스트 40개 및 53개 subtests 통과; MATCH/ERROR만 전송하고 NO_MATCH는 네트워크를 호출하지 않으며, 실패 시 토큰/응답 본문을 노출하지 않는다.
- 주문 비연결 검증: scan entrypoint/scanner/Telegram sink의 AST에 order/broker import와 `buy_market`/`sell_market`/`submit_order` 호출이 없고, 관련 안전 테스트가 통과했다.
- 재개 조건:
  1. 정확한 Vercel `breadday99-3014/kiwoom-trader` Production 환경에 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`를 등록한다.
  2. 토큰을 문서, 커밋, 로그, 오류 메시지에 남기지 않는다.
  3. 먼저 MATCH와 ERROR 각각 실제 Telegram 수신을 확인한다.
  4. 실제 전송은 결과 sink에 한정하고 주문 실행 경로는 계속 연결하지 않는다.

## 4. ORB/BULL_FLAG 실데이터 최적화 및 portfolio recommender

- 상태: 명세 보류
- 이유: 승인된 OHLCV 데이터 계약, 거래비용, 슬리피지, 체결 가정, 추천 기준이 확정되지 않았다.
- 현재 정책: 임의의 기본 전략이나 합성 신호를 만들지 않고 fail-closed로 유지한다.
- 재개 조건: 데이터 계약과 평가 기준을 먼저 문서화하고, 각 동작에 대해 failing test를 작성한 뒤 구현한다.

## 5. FACTOR 8종목 실제 백테스트

- 상태: 부분 조회 성공 / 백테스트 보류
- 조회 성공: 8개 중 6개 종목에서 312개 일봉 확보.
- 데이터 없음: `061220`, `416770`은 모의투자 API에서 종목정보와 일봉 모두 빈 응답을 반환했다.
- 정책: 승인된 유니버스가 모두 채워지지 않은 상태에서 종목을 제외하거나 합성 데이터를 넣지 않는다.
- 재개 조건: 해당 종목의 유효한 일봉 데이터가 모의 API에 제공되거나, 운영자가 새로운 승인 유니버스와 데이터 계약을 지정한다.

## 확인 명령

외부 조건이 준비되기 전까지는 다음 오프라인 검증을 반복한다.

```bash
python -m pytest -q
python -m compileall -q api strategies tests
```
