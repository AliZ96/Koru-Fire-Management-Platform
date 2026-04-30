from __future__ import annotations

from typing import Any

import requests
from fastapi import HTTPException

from app.core.config import settings


class FirebaseIdentityService:
    @staticmethod
    def sign_in_with_email_password(email: str, password: str) -> dict[str, Any]:
        api_key = (settings.FIREBASE_WEB_API_KEY or "").strip()
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="FIREBASE_WEB_API_KEY is not configured",
            )

        url = (
            "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
            f"?key={api_key}"
        )
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }
        try:
            response = requests.post(url, json=payload, timeout=20)
        except requests.RequestException as exc:
            raise HTTPException(status_code=503, detail=f"Firebase auth service unavailable: {exc}")

        if response.status_code == 200:
            return response.json()

        try:
            err = response.json()
            message = (
                err.get("error", {}).get("message")
                or err.get("error_description")
                or "INVALID_CREDENTIALS"
            )
        except Exception:
            message = "INVALID_CREDENTIALS"

        if message in {"INVALID_LOGIN_CREDENTIALS", "EMAIL_NOT_FOUND", "INVALID_PASSWORD"}:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        raise HTTPException(status_code=502, detail=f"Firebase login failed: {message}")
