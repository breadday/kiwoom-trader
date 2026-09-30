# 개발 환경 설정

이 문서는 컴퓨터별 절대경로가 아닌 **저장소 루트**를 기준으로 합니다.
저장소를 어느 드라이브에 clone해도 동일한 명령을 사용할 수 있습니다.

## 1. 저장소 준비

```bash
git clone https://github.com/breadday/kiwoom-trader.git
cd kiwoom-trader
```

이미 clone한 경우에는 저장소 루트에서 최신 내용을 받습니다.

```bash
git pull origin main
```

## 2. Python 가상환경

Windows:

```bash
python -m venv .venv
.venv\\Scripts\\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pytest
```

macOS/Linux/WSL:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pytest
```

## 3. 테스트

```bash
python -m pytest -q
```

## 4. Docker 선택 설정

Docker가 필요한 작업은 저장소 루트에서 실행합니다. Docker Compose 파일이 있는 경우:

```bash
docker compose up -d
```

호스트의 절대경로를 컨테이너에 직접 연결해야 하는 경우에는 각 컴퓨터의 Docker 설정에서
현재 저장소 루트를 `${PROJECT_ROOT}`로 지정하고, 문서나 코드에 특정 드라이브 문자를
기록하지 않습니다.

## 5. 환경변수와 비밀정보

API 키, Telegram 토큰 등 비밀정보는 저장소에 commit하지 않습니다.
필요한 값은 로컬 환경변수 또는 로컬 전용 `.env` 파일로 관리하고, `.gitignore`에 등록합니다.
실거래 인증정보는 테스트 환경에 넣지 않습니다.
