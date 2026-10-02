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

- 상태: 완료 / Telegram runtime 전송도 완료
- 결과: deployment `dpl_E1ahxTWJDjHavnU7xhLhPAss5JwM`이 `READY` 상태로 production에 반영되었다.
- read-back: `https://kiwoom-trader.vercel.app/` 및 `/api/index.py`가 모두 `{"ok": true, "mode": "paper", "readonly": true}`를 반환했다.
- 현재 준비: Vercel production env 목록에서 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 등록을 확인했다.
- 안전 범위: 현재 entrypoint는 paper-only이며 live 주문 전환을 허용하지 않는다.
- 확인: Production env 이름 read-back, 로컬 ignored env runtime 주입, MATCH/ERROR API 성공 응답을 모두 확인했다.

## 3. Telegram 운영 전송

- 상태: 완료
- 결과: 로컬 ignored env에서 secret을 런타임에만 주입하고 Telegram API 인증 및 configured chat 대상 전송을 확인했다. MATCH 1건과 ERROR 1건이 각각 `True`로 반환되었다.
- 제한: Telegram `getUpdates`에는 최근 chat update가 없어 수신 메시지 read-back은 수행하지 못했다. API의 `sendMessage` 성공 응답은 확인했다.
- 안전 검증: fake transport 기반 Telegram 테스트 40개 및 53개 subtests 통과; MATCH/ERROR만 전송하고 NO_MATCH는 네트워크를 호출하지 않으며, 실패 시 토큰/응답 본문을 노출하지 않는다.
- 주문 비연결 검증: scan entrypoint/scanner/Telegram sink의 AST에 order/broker import와 `buy_market`/`sell_market`/`submit_order` 호출이 없고, 관련 안전 테스트가 통과했다.
- 운영 주의: 토큰은 문서, 커밋, 로그, 오류 메시지에 남기지 않으며 `.env.local`은 ignored 상태를 유지한다.

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

## 6. Gate 0 rewritten-ref publication

- 상태: 안전한 preflight에서 중단 / 원격 write 없음
- 결과: `automation/guarded-history-push.ps1` dry-run이 expected rewritten commit `b54e785bc1c9d65f1d034ae6d3f55b1ae199c4c1`를 현재 checkout에서 찾지 못해 중단했다.
- 추가 관측: 현재 원격 heads도 문서의 2026-09-27 old-SHA snapshot과 달라졌다(`main`은 현재 작업 커밋, STEP 07은 `c2d7bad...`). 따라서 기존 seven-ref mapping을 추정해 force-push하지 않는다.
- 안전 범위: 원격 ref/tag는 변경하지 않았다. 일반 main 작업과 Telegram/배포 상태는 보존된다.
- 재개 조건:
  1. 원래 filtered mirror 또는 새로 재생성한 verified rewrite bundle에서 다섯 filtered target commit과 최종 STEP 07F commit을 확보한다.
  2. 정확한 대상 ref와 old-SHA snapshot을 현재 GitHub에서 다시 승인·고정한다.
  3. 별도 명시 승인 후 guarded script의 `-Execute -ConfirmRewrite`를 실행하고 seven-ref post-push SHA를 read-back한다.

## 7. NH/기타 broker 실 API 연동

- 상태: mock/paper 안전 경계만 구현 / 실 API 연동 보류
- 위치: `api/multi_broker_api_1.py`, `api/multi_broker_api_2.py`, `api/multi_broker_api_3.py`
- 이유: broker별 인증, endpoint, rate limit, 잔고·주문 계약이 승인·검증되지 않았다.
- 현재 안전 범위: mock/paper 검증과 비-paper fail-closed만 허용한다. TODO 주석을 실제 네트워크 호출로 대체하지 않는다.
- 재개 조건: broker별 공식 API 계약과 승인된 paper credential을 별도로 제공하고, read-only fixture·failing test·bounded smoke를 먼저 추가한다.

## 확인 명령

외부 조건이 준비되기 전까지는 다음 오프라인 검증을 반복한다.

```bash
python -m pytest -q
python -m compileall -q api strategies tests
```
