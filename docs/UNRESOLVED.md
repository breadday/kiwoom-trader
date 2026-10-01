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

- 상태: CLI 설치 완료 / 계정 인증·프로젝트 연결 보류
- 이유: Vercel CLI 인증, 프로젝트 연결, 환경변수 등록 권한과 네트워크가 필요하다.
- 현재 준비: Vercel CLI `62.1.0` 설치 완료.
- 안전 범위: 현재 entrypoint는 paper-only이며 live 주문 전환을 허용하지 않는다.
- 재개 조건:
  1. 승인된 Vercel 프로젝트와 CLI 로그인이 준비된다.
  2. `KIWOOM_APP_KEY`, `KIWOOM_APP_SECRET`을 Vercel secret store에만 등록한다.
  3. `docs/deployment.md`의 배포 전 테스트를 통과한다.
  4. 배포 후 endpoint 응답과 로그를 read-back하여 paper-only 상태를 확인한다.

## 3. Telegram 운영 전송

- 상태: 보류
- 이유: 운영자가 제공하고 승인한 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`와 외부 네트워크가 필요하다.
- 재개 조건:
  1. 토큰과 채팅 ID를 환경변수로만 주입한다.
  2. 토큰을 문서, 커밋, 로그, 오류 메시지에 남기지 않는다.
  3. 먼저 fake transport 테스트를 통과한다.
  4. 실제 전송은 MATCH/ERROR 결과에 한정하고, 주문 실행과 연결하지 않는다.

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
