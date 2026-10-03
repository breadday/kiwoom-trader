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

- 상태: 정상 동작 검증 완료 / 전략 변경 전까지 최적화·추천 보류
- 구현: `api/kiwoom_api.py`가 모의투자 `ka10080` 1분봉을 정규화하고, `automation/kiwoom_intraday_backtest.py`가 ORB와 BULL_FLAG를 다음 봉 시가 체결 방식으로 시뮬레이션한다.
- 확인: `005930` 모의투자 1분봉 조회 및 기준 비용 실행 성공; 오프라인 전체 테스트 182개 통과.
- 적용 기준: 수수료 0.015%(`0.00015`), 매도 세율 0.15%(`0.00150`), 슬리피지 0.10%(`0.00100`); 거래량 기준 50%와 70%를 비교했다.
- 실행 결과: 두 설정 모두 `days=2`, `trades=1`, 수익률 `-0.005604`, MDD `0.005604`로 동일했다.
- 남은 조건: 현재 표본은 2거래일·1거래라 전략 선택 기준을 충족하지 않는다. 최소 30거래 이상 또는 승인된 더 긴 기간의 1분봉을 확보한 뒤 재검증한다.
- 추천 기준: 기준 시나리오 수익률 양수, 스트레스 시나리오 손실 제한, MDD 15% 이하, 최소 30거래, 수익률 40%·MDD 안정성 35%·Sharpe 25% 종합점수.
- 안전 범위: read-only 시장데이터만 사용하며 주문 API는 호출하지 않는다.

## 5. FACTOR 6종목 실제 백테스트

- 상태: 데이터 확인된 6종목으로 진행
- 조회 성공: `005935`, `067310`, `086520`, `253590`, `272210`, `441680`에서 각 312개 일봉 확보.
- 제외: `061220`, `416770`은 모의투자 API에서 종목정보와 일봉이 빈 응답을 반환해 승인 유니버스에서 제외했다.
- 정책: 데이터가 없는 종목은 합성하거나 임의 보간하지 않고 유니버스에서 제외한다.
- 재개 조건: 제외 종목의 유효한 일봉 데이터가 제공되면 별도 승인 후 유니버스 복귀를 검토한다.

## 6. Gate 0 rewritten-ref publication

- 상태: 완료 / 원격 read-back 확인
- 결과: GitHub 원격에 `main`과 sanitized STEP 07F를 포함한 7개 branch ref가 반영되어 있다.
- 현재 `main` 및 STEP 07F: `c819934c9f5b94c192bf9e88fb9a3b434f4dd5c9`
- 기타 rewritten refs: STEP 07=`51ecae94a5666874079b83cf2a212c105b09c925`, STEP 07B=`6966a33daeb91bdb6dca5bc265f6a8038d5548bf`, STEP 07C=`56c8b8efc5568411b29c95402721428a9d658089`, STEP 07D=`5f888320fa31ac1eff7eb54e91f150e9560cd106`, STEP 07E=`8219afc718936e56c1a8ba5adad998f33f848248`.
- 확인: 원격 `main`과 local fresh checkout SHA가 일치하며, legacy `kiwoom_rescue_bot.py`는 없고 `automation/kiwoom_rescue_demo.py`가 존재한다.
- 안전 범위: history rewrite force-push는 추가로 수행하지 않는다. 이후 변경은 일반 branch/PR 절차를 사용한다.

## 확인 명령

외부 조건이 준비되기 전까지는 다음 오프라인 검증을 반복한다.

```bash
python -m pytest -q
python -m compileall -q api strategies tests
```
