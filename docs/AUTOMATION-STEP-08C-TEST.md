# 자동 개발 STEP 08C — read-only provider와 백테스트 경계 테스트

## 테스트 증거

| 테스트 | 검증 |
|---|---|
| `test_partial_threshold_sells_half_and_marks_remainder_at_last_close` | RESCUE provider `limit=60` 및 결과 계약 |
| `test_rescue_grid_fetches_daily_history_once_for_all_parameter_sets` | grid search가 동일 snapshot 1회 재사용 |
| `test_factor_universe_fetches_312_bars_once_per_symbol` | FACTOR 8종목 × `limit=312` |
| `test_requires_exact_requested_history_and_never_uses_mock_fallback` | RESCUE 불충분 history fail-closed |
| `test_factor_universe_rejects_short_provider_history_before_scoring` | FACTOR 불충분 history fail-closed |
| `test_propagates_read_only_provider_failure_without_mock_fallback` | provider 오류 원문 전달 |
| `test_factor_universe_rejects_misaligned_dates` | 종목 간 날짜축 불일치 거부 |

## 안전 경계

- provider는 모두 fake/fixture 기반이다.
- optimizer는 `KiwoomAPI`의 주문 메서드를 호출하지 않는다.
- 실제 API page size/rate limit을 확인하기 전에는 자동 확장·재시도 정책을 추가하지 않는다.
