# Kiwoom Trader Agent Rules

## 금지 파일 (절대 읽지 마)
config_live.py
.env
*.key
token.json
accounts.yaml

## 폴더 규칙
- API: kiwoom_trader/api/
- 전략: strategies/
- 테스트: tests/
- 문서: docs/

## 커밋 규칙
- feat: / fix: / chore: 로 시작

## 개발 환경
- Docker 컨테이너 kiwoom-dev 안에서 pytest
