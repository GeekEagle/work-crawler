from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from pathlib import Path
from urllib import error, parse, request

AUTHORIZATION_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"


@dataclass(frozen=True)
class LinkedInConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: tuple[str, ...] = ("openid", "profile", "email")

    @classmethod
    def from_env_or_file(cls, env: dict[str, str] | None = None, config_path: str = "llm-config.txt") -> "LinkedInConfig":
        import os
        values = dict(os.environ if env is None else env)
        if Path(config_path).exists():
            for line in Path(config_path).read_text(encoding="utf-8-sig").splitlines():
                if "=" not in line and ":" not in line:
                    continue
                separator = "=" if "=" in line else ":"
                key, value = line.split(separator, 1)
                key = key.strip().lower().replace(" ", "_")
                value = value.strip()
                if key in {"linkedin_client", "linkedin_client_id"}:
                    values.setdefault("LINKEDIN_CLIENT_ID", value)
                elif key in {"primary_client_secret", "linkedin_client_secret"}:
                    values.setdefault("LINKEDIN_CLIENT_SECRET", value)
                elif key in {"linkedin_redirect_uri", "redirect_uri"}:
                    values.setdefault("LINKEDIN_REDIRECT_URI", value)
        missing = [name for name in ("LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET", "LINKEDIN_REDIRECT_URI") if not values.get(name)]
        if missing:
            raise ValueError("Missing LinkedIn configuration: " + ", ".join(missing))
        scopes = tuple(filter(None, values.get("LINKEDIN_SCOPES", "openid profile email").split()))
        return cls(values["LINKEDIN_CLIENT_ID"], values["LINKEDIN_CLIENT_SECRET"], values["LINKEDIN_REDIRECT_URI"], scopes)


def authorization_url(config: LinkedInConfig, state: str | None = None) -> tuple[str, str]:
    state = state or secrets.token_urlsafe(32)
    query = parse.urlencode({
        "response_type": "code", "client_id": config.client_id,
        "redirect_uri": config.redirect_uri, "state": state,
        "scope": " ".join(config.scopes),
    })
    return f"{AUTHORIZATION_URL}?{query}", state


def exchange_code(config: LinkedInConfig, code: str) -> dict:
    body = parse.urlencode({
        "grant_type": "authorization_code", "code": code,
        "redirect_uri": config.redirect_uri, "client_id": config.client_id,
        "client_secret": config.client_secret,
    }).encode()
    req = request.Request(TOKEN_URL, data=body, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (error.HTTPError, error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"LinkedIn token exchange failed: {exc}") from exc


def get_userinfo(access_token: str) -> dict:
    req = request.Request(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
    try:
        with request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (error.HTTPError, error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"LinkedIn userinfo request failed: {exc}") from exc
