# AUTOMATION
자동화 진행상황

- [x] daily.py 캐싱
- [ ] 주문 자동화
- [ ] 스캔 자동화
- [ ] 텔레그램 알림

진행할 때마다 여기에 적고 Codex에게 시킴

## daily.py 캐싱 구현

- `api/daily.py`의 메모리 캐시를 `KiwoomAPI.get_daily_chart()`에 연결.
- API 인스턴스별 보관, TTL 300초, 최대 128개 항목(LRU). 프로세스 종료 시 소멸하며 디스크에는 저장하지 않음.
- 키: API URL, 종목코드, 확정된 기준일(KST 기본값 포함), limit, max_pages, 수정주가 구분.
- 검증 및 페이지 조회가 성공한 비어 있지 않은 결과만 저장. 오류와 빈 결과는 다음 요청에서 재조회.
- 반환값은 복사하여 호출자의 수정이 캐시를 오염시키지 않음.
- `get_daily_chart("005930", refresh=True)`로 해당 조건을 무효화하고 재조회.
- `api.clear_daily_cache()`로 인스턴스 전체 캐시 삭제.
- 기본값 및 명시적 당일 조회 모두 TTL 적용: 최신 값이 즉시 필요하면 `refresh=True` 사용.
