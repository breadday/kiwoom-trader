import requests
import time

class KiwoomAuth:
    '''키움 REST API 토큰 관리 - KIS 템플릿의 kis_auth.py 역할'''
    def __init__(self, app_key, app_secret, base_url="https://api.kiwoom.com"):
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = base_url
        self.token = None
        self.expires_at = 0

    def get_token(self):
        if self.token and time.time() < self.expires_at - 60:
            return self.token
        url = f"{self.base_url}/oauth2/token"
        resp = requests.post(url, json={
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret
        })
        resp.raise_for_status()
        data = resp.json()
        self.token = data.get("token") or data.get("access_token")
        # 키움 토큰은 24시간 유효
        self.expires_at = time.time() + 23*3600
        print(f"[AUTH] 토큰 발급 완료: {self.token[:20]}...")
        return self.token

    def headers(self):
        return {"Authorization": f"Bearer {self.get_token()}", "Content-Type": "application/json"}
