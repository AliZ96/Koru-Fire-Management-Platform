from fastapi import APIRouter, Depends

from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.services.auth_service import AuthService
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


@router.get("/me")
def read_me(current_user: dict = Depends(get_current_user)):
    return current_user
