from fastapi import APIRouter, Depends, HTTPException
from jose import jwt as jose_jwt
from pydantic import BaseModel

from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.core.security import create_access_token
from app.services.auth_service import AuthService
from app.core.security import get_current_user, create_access_token
from app.db.session import get_db
from app.core.security import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/user/register", response_model=TokenResponse)
def user_register(payload: RegisterRequest):
    token = AuthService.register_user(payload.username, payload.password)
    return TokenResponse(access_token=token)


@router.post("/user/login", response_model=TokenResponse)
def user_login(payload: LoginRequest):
    token = AuthService.login_user(payload.username, payload.password)
    return TokenResponse(access_token=token)


@router.post("/firefighter/register", response_model=TokenResponse)
def firefighter_register(payload: RegisterRequest):
    token = AuthService.register_firefighter(payload.username, payload.password)
    return TokenResponse(access_token=token)


@router.post("/firefighter/login", response_model=TokenResponse)
def firefighter_login(payload: LoginRequest):
    token = AuthService.login_firefighter(payload.username, payload.password)
    return TokenResponse(access_token=token)


@router.post("/personnel/login", response_model=TokenResponse)
def personnel_firebase_login(payload: LoginRequest):
    """Yetkili personel: Firebase e-posta/şifre; Firestore users'da role=admin olmalı."""
    token = AuthService.login_personnel_firebase(payload.username, payload.password)
    return TokenResponse(access_token=token)


@router.get("/me")
def read_me(current_user: dict = Depends(get_current_user)):
    return current_user


class FirebaseTokenRequest(BaseModel):
    firebase_token: str


class UserSyncRequest(BaseModel):
    firebase_uid: str | None = None
    display_name: str | None = None
    role: str = "user"


@router.post("/firebase-token", response_model=TokenResponse)
def firebase_token_exchange(payload: FirebaseTokenRequest):
    """Firebase JWT'yi backend JWT'ye çevirir (pipeline ve API auth için)."""
    try:
        claims = jose_jwt.get_unverified_claims(payload.firebase_token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Firebase token okunamadı: {exc}")

    email = claims.get("email") or claims.get("sub") or ""
    if not email:
        raise HTTPException(status_code=400, detail="Firebase token'da email bulunamadı")

    role = AuthService.resolve_jwt_role_for_firebase_email(email)
    backend_token = create_access_token(data={"sub": email, "email": email, "role": role})
    return TokenResponse(access_token=backend_token)


@router.post("/user/sync")
def sync_user_profile(payload: UserSyncRequest, current_user: dict = Depends(get_current_user)):
    username = str(current_user.get("sub") or "")
    role = str(payload.role or current_user.get("role") or "user").lower()
    if not username:
        raise HTTPException(status_code=401, detail="Unauthorized")

    row = AuthService.sync_user_profile(
        username=username,
        role=role,
        firebase_uid=payload.firebase_uid,
        display_name=payload.display_name,
    )
    return {"ok": True, "user_id": row.get("id"), "username": username}
