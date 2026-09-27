# SETUP
Docker + Hermes + Codex 셋팅

1. cd E:\hermes-local
2. docker compose up -d
3. docker run -d --name kiwoom-dev -v E:\hermes-local\workspace\kiwoom_trader:/app -w /app python:3.11 tail -f /dev/null
4. WSL: curl -fsSL https://chatgpt.com/codex/install.sh | sh && codex login
