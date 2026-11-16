import requests

from app.config.settings import settings


def get_json(url: str, params: dict | None = None):
    headers = {"User-Agent": "FinBot-FATEC/1.0"}
    token = settings.brapi_token.get_secret_value() if settings.brapi_token else ""
    if token and "brapi.dev" in url:
        headers["Authorization"] = f"Bearer {token}"
    resposta = requests.get(url, params=params, headers=headers, timeout=15)
    resposta.raise_for_status()
    return resposta.json()