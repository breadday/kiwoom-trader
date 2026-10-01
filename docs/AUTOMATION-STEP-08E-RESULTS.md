# 자동 개발 STEP 08E — read-only market-data 검증 결과

## 상태

- 상태: `READ_ONLY_SMOKE_PASS_PAPER`
- 기준일: 2026-10-01
- 계좌·주문 데이터: 접근하지 않음
- 실제 Kiwoom endpoint: 모의투자 read-only 일봉 조회 1회 성공

## 완료된 사전 검증

- `test_08e_smoke.py`의 오프라인 smoke 2개 통과
- `KIWOOM_APP_KEY`·`KIWOOM_APP_SECRET` env 주입과 `is_paper=True` 확인
- 동일 일봉 요청의 cache hit 및 `paper=False` 주문 fail-closed 확인
- Kiwoom daily-chart·optimizer를 포함한 집중 회귀 52개 통과
- `python -m compileall -q api tests` 통과
- `git diff --check` 통과
- `get_daily_chart()`의 URL, `ka10081`, continuation, normalization 경계는
  fixture 테스트로 검증됨
- 키움 CLI가 내보낸 모의투자 자격증명을 메모리에만 주입하고
  `https://mockapi.kiwoom.com`의 `005930` 일봉을 실제 조회함
- 실제 smoke 결과: 토큰 발급 성공, 5개 행, `20260922`~`20260930`
- 재현 명령은 `automation/kiwoom_readonly_smoke.py`에 기록함

## 아직 남은 검증 범위

1. 운영(real) endpoint와 실계좌 인증은 실행하지 않는다.
2. repository-local `.tmp-pydeps`의 NumPy/Pandas native wheel이 CPython 3.14용이고
   현재 실행기는 Python 3.11이어서 전체 privacy discovery가 import 실패한다.
3. Python 3.11용 dependency 설치는 현재 프로젝트 venv와 CI에서 완료했다.
4. 실제 page size, rate limit, 휴장일, 정렬, 가격 부호, 수정주가 의미는
   fixture만으로 운영 호환성을 증명할 수 없다.

## 결론

모의투자 read-only smoke는 성공으로 표시한다. 운영 endpoint·실계좌·주문은
여전히 실행하지 않으며, credential·계좌·주문 데이터도 보존하지 않는다.
