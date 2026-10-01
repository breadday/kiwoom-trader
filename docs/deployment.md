# Kiwoom Trader 배포 및 실전 전환 안전 가이드

## 현재 지원 범위

현재 저장소는 오프라인·fixture·paper/mock 검증과 read-only 일봉 조회 경계를
제공한다. 실계좌 주문 제출은 지원 범위가 아니며, `paper=False` 주문은
fail-closed여야 한다.

현재 저장소에는 Vercel Python entrypoint(`api/index.py`)와 함수 설정
(`vercel.json`)이 있다. entrypoint는 `KIWOOM_APP_KEY`와
`KIWOOM_APP_SECRET`을 환경변수에서 읽고 `paper=True`를 고정하며,
broker 요청 없이 read-only 상태만 반환한다. 실제 endpoint 호출은 별도
승인 전까지 연결하지 않는다.

## 배포 전 필수 검사

```powershell
git status --short --branch
$env:PYTHONPATH=(Resolve-Path .tmp-pydeps).Path
python -m unittest discover -s tests -p 'test_*.py' -q
python -m compileall -q api tests
git diff --check
```

- 전체 테스트가 `OK`가 아니면 배포하지 않는다. 현재 프로젝트 검증은
  `177 passed, 121 subtests passed`이며, CPython 3.14용
  `.tmp-pydeps`를 사용할 때는 반드시 CPython 3.14 interpreter로 실행한다.
- `accounts.yaml`, `.env`, `config_live.py`, `*.key`, `token.json`을 commit하지 않는다.
- API key, secret, token, account number를 로그·fixture·문서·채팅에 출력하지 않는다.
- 합성 데모 결과를 실거래 성과나 매수 추천으로 표시하지 않는다.

## paper/live 안전 규칙

1. 기본 모드는 `paper=True`로 유지한다.
2. `KiwoomAPI.buy_market()`와 `sell_market()`은 `paper=False`에서
   `LiveOrderDisabledError`를 발생시켜야 한다.
3. `MultiAccountManager`와 각 broker adapter의 비-paper 주문 및 live 잔고 조회
   차단 테스트가 통과해야 한다. `accounts.yaml` 누락 시 암묵적 mock 계좌를
   생성하지 않으며 명시적 `accounts:` 목록이 필요하다.
4. `get_daily_chart()`는 read-only 시장데이터 경로지만 Bearer 인증이
   필요하므로, 별도 승인 전 실제 endpoint를 호출하지 않는다.
5. 실전 전환을 위해서는 별도의 사용자 승인, 키 관리, 주문 승인 회로,
   kill switch, 감사 로그, 소액 paper 검증 절차를 먼저 설계하고 검토한다.

## 환경변수·secret 운영 원칙

- secret은 Vercel/호스팅 제공자의 암호화된 secret store에만 저장한다.
- 저장소 파일에 secret을 복사하거나 build artifact에 포함하지 않는다.
- 환경변수는 `KiwoomAPI` 생성 시 `KiwoomAuth` 구성에만 사용하며, 값은
  출력·저장하지 않는다.
- 실제 endpoint 호출을 연결한 배포는 read-only 승인과 secret 운영 검토
  전까지 진행하지 않는다.
- secret 노출이 의심되면 즉시 사용 중지·회전하고 로그와 build artifact를
  점검한다.

Vercel 프로젝트 연결과 CLI 인증이 준비된 승인 환경에서만 다음을 실행한다.

```powershell
vercel env add KIWOOM_APP_KEY
vercel env add KIWOOM_APP_SECRET
vercel --prod
```

입력한 secret 값과 access token은 명령 출력이나 배포 로그에 남기지 않는다.

## 단계적 운영 순서

1. 오프라인 fixture 및 전체 테스트 통과
2. 승인된 모의투자 환경에서 read-only `ka10081` smoke test 통과
3. 응답 page size/rate limit/휴장일/가격 부호 확인
4. paper/mock 주문 안전성 회귀 확인
5. 배포 대상과 데이터 보존 범위에 대한 사용자 승인
6. 별도 실전 전환 승인 전까지 live order는 비활성 유지

## 현재 미완료 항목

- GitHub rewritten refs의 atomic publication 및 원격 SHA readback
- 운영(real) Kiwoom endpoint와 실계좌 read-only 검증
- Vercel 프로젝트 연결, secret 등록, production 배포 및 로그 readback
- 실전 주문 전환 승인 및 운영 통제

Gate 0 원격 publication은 저장소의
`automation/guarded-history-push.ps1`를 사용한다. 기본 실행은 preflight
검사만 수행하며, 실제 쓰기는 명시적으로 `-Execute -ConfirmRewrite`를
지정한 경우에만 실행된다. 이 스크립트는 정확한 old-SHA snapshot, 빈 tag
목록, 7개 ref 집합, `--force-with-lease`, push 후 SHA readback을 강제한다.
