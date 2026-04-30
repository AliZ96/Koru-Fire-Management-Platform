from __future__ import annotations

from pathlib import Path
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore

from app.core.config import settings

_firebase_app: Optional[firebase_admin.App] = None
_firestore_client: Optional[firestore.Client] = None


def _resolve_credential_path() -> Optional[str]:
    raw = (settings.FIREBASE_CREDENTIALS_PATH or "").strip()
    if not raw:
        return None
    return str(Path(raw).expanduser().resolve())


def get_firebase_app() -> firebase_admin.App:
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    cred_path = _resolve_credential_path()
    options = {"projectId": settings.FIREBASE_PROJECT_ID}
    if cred_path:
        cred = credentials.Certificate(cred_path)
        _firebase_app = firebase_admin.initialize_app(cred, options=options)
    else:
        _firebase_app = firebase_admin.initialize_app(options=options)
    return _firebase_app


def get_firestore_client() -> firestore.Client:
    global _firestore_client
    if _firestore_client is None:
        app = get_firebase_app()
        _firestore_client = firestore.client(app=app)
    return _firestore_client
