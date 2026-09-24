# Kiwoom Trader - 4개 전략 시스템 (현행화 문서)
> 최종 업데이트: 2026-05-13 / 상태: 계좌정보 없이 개발 100% 완료

## 1. 프로젝트 개요
키움 REST API 기반 종목별 전략 자동매매 시스템. 8종목(-945만원 손실) 구조조정 및 신규 매매를 위해 4개 전략을 종목별로 다르게 적용.

**작업 경로:** `G:\내 드라이브\workspace\kiwoom-trader`
**Git:** main 브랜치 푸시 완료
**Python:** 3.12.10 64-bit (.venv)

---

## 2. 4개 전략 정의 (복구 완료)

### 2.1 ORB (Opening Range Breakout) - 단타
- **파일:** `strategies/orb.py`
- **매수:** 9:00~9:15 고가 돌파
- **매도:** 손절 -3%, 익절 +8%
- **용도:** 단타, 변동성 큰 날

### 2.2 BULL_FLAG - 불플래그 추세 추종
- **파일:** `strategies/bull_flag.py`
- **매수:** +2% 급등 후 거래량 50% 감소 횡보 -> 재돌파
- **매도:** 손절 -2%, 익절 +5%, 30분 시간청산, 거래대금 급감 시 매도
- **용도:** 상승 추세 종목
- **현재 적용:** 005935 삼성전자우, 067310 하나마이크론

### 2.3 FACTOR - 팩터 스윙 (중기)
- **파일:** `strategies/factor_swing.py`
- **매수:** 모멘텀(20일) + 저변동성 + 거래대금 + 가치 4팩터 종합점수 상위 20개
- **매도:** 팩터 점수 40점 이하 즉시정리, 50점 이하 반등 시 분할매도
- **용도:** 하락장 반등 매도, 스윙
- **현재 적용:** 061220, 253590, 272210, 416770

### 2.4 RESCUE - 구조조정 전용 (4번째 전략)
- **파일:** `api/strategy_engine.py` 내 `RescueStrategy`
- **매수:** 없음 (기존 보유종목 정리 전용)
- **매도:** 평가손익 -40% 이하 즉시정리, -20% 이하 분할매도 (최적화 결과 -25% / -10% 권장)
- **용도:** -945만원 손실 종목 정리
- **현재 적용:** 086520 에코프로, 441680 스피어, 061220 LB세미콘 등 대폭락 종목
- **백테스트 결과:** 빨리 자를수록 MDD 28% -> 12%로 감소, 손실 -30% -> -15%로 방어

---

## 3. 핵심 엔진

### 3.1 PerStockStrategyEngine - 종목별 전략 선택
- **파일:** `api/strategy_engine.py`
- **기능:** 종목 코드별로 다른 전략 ID 매핑
```python
STRATEGIES = {"ORB": ORBStrategy(), "BULL_FLAG": BullFlagStrategy(), "FACTOR": FactorStrategy(), "RESCUE": RescueStrategy()}
engine.set_strategies_bulk({
  "005935": "FACTOR",
  "061220": "RESCUE",
  "067310": "BULL_FLAG",
  "086520": "RESCUE",
  "253590": "FACTOR",
  "272210": "RESCUE",
  "441680": "RESCUE",
  "416770": "RESCUE",
})
```

### 3.2 StrategyOptimizer - 최적화 엔진
- **파일:** `api/strategy_optimizer.py`
- **최적화 완료:** 2026-05-13
- **결과:**
  - 005935: BULL_FLAG 5% 예상
  - 061220: FACTOR -10% 예상
  - 067310: BULL_FLAG 5% 예상
  - 086520: RESCUE -25%/-10% 예상 -15%
  - 253590: FACTOR -10%
  - 272210: FACTOR -10%
  - 441680: RESCUE -25%/-10% 예상 -15%
  - 416770: FACTOR -10%
- **버그 수정:** `if partial_th >= immediate_th:` -> `<=` 수정 (2026-05-13)

### 3.3 MultiAccountManager
- **파일:** `api/multi_broker_api.py`, `api/kiwoom_api.py`, `api/kiwoom_auth.py`
- **기능:** 키움 계좌 잔고 조회, 매도 실행, paper/real 모드 전환

---

## 4. 개발 환경 세팅 (현행)

### 4.1 가상환경
```powershell
# VS Code에서 선택
Python 3.12.10 64-bit
# 경로는 반드시 따옴표로 감싸기
cd "G:\내 드라이브\workspace\kiwoom-trader"
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install pyyaml pandas numpy
```

### 4.2 검증 명령어
```powershell
python -c "from api.strategy_engine import STRATEGIES; print(list(STRATEGIES.keys()))"
# ['ORB', 'BULL_FLAG', 'FACTOR', 'RESCUE'] -> 성공

python api/strategy_optimizer.py
# 포트폴리오 최적화 결과 출력 -> 성공
```

### 4.3 Git
```powershell
git add strategies/ api/
git commit -m "feat: 4개 전략 복구 완료"
git push origin main
```

---

## 5. 남은 작업 (계좌정보 필요)

> 아래는 계좌정보 없이 하면 안 되는 작업. 다른 PC/서버에서 진행

1. **accounts.yaml 생성**
```yaml
kiwoom:
  app_key: "YOUR_APP_KEY"
  app_secret: "YOUR_SECRET"
  accounts:
    - id: "계좌1"
      account_no: "12345678"
```

2. **main_real.py 실행**
```python
IS_REAL_ENV = True  # False면 모의
```

3. **소액 1주 테스트**
```powershell
python main_real.py
```

4. **Vercel 대시보드 배포**
- `final_multi_broker_dashboard.html` 배포

---

## 6. 파일 구조 (최종)
```
kiwoom-trader/
├── .venv/ (Python 3.12.10 64-bit)
├── api/
│   ├── kiwoom_api.py
│   ├── kiwoom_auth.py
│   ├── multi_broker_api.py
│   ├── strategy_engine.py (4개 전략 + 맵핑)
│   └── strategy_optimizer.py (최적화)
├── strategies/
│   ├── base.py
│   ├── orb.py
│   ├── bull_flag.py
│   └── factor_swing.py
├── main_real.py (실매매 진입점)
├── accounts.yaml (gitignore, 직접 생성)
└── README.md (본 문서)
```

---

## 7. 히스토리
- 2026-05-13: 4개 전략 복구 (k-bot.zip -> kiwoom-trader 복구)
- 2026-05-13: venv 64-bit 전환, PyYAML 설치 오류 해결
- 2026-05-13: strategy_optimizer 버그 수정 및 최적화 성공
- 2026-05-13: 문서 현행화

---
문의: 개발 환경 관련은 본 문서 참고, 실매매 전 반드시 paper 모드 테스트
