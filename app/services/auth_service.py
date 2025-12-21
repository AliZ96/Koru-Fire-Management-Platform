from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.repositories.auth_repo import AuthRepositoryPG


def _validate_password(password: str) -> str:
    password = (password or "").strip()
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Password too long (bcrypt limit 72 bytes)")
    return password


class AuthService:
    @staticmethod
    def register_user(username: str, password: str, db: Session) -> str:
        repo = AuthRepositoryPG(db)

        existing = repo.get_by_username_and_role(username, "user")
        if existing:
            raise HTTPException(status_code=400, detail="User already exists")

        password = _validate_password(password)
        hashed = hash_password(password)

        repo.create_user(username, hashed, "user")
        return create_access_token({"sub": username, "role": "user"})

    @staticmethod
    def login_user(username: str, password: str, db: Session) -> str:
        repo = AuthRepositoryPG(db)

        user = repo.get_by_username_and_role(username, "user")
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        password = _validate_password(password)
        if not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return create_access_token({"sub": username, "role": "user"})

    @staticmethod
    def register_firefighter(username: str, password: str, db: Session) -> str:
        repo = AuthRepositoryPG(db)

        existing = repo.get_by_username_and_role(username, "firefighter")
        if existing:
            raise HTTPException(status_code=400, detail="User already exists")

        password = _validate_password(password)
        hashed = hash_password(password)

        repo.create_user(username, hashed, "firefighter")
        return create_access_token({"sub": username, "role": "firefighter"})

    @staticmethod
    def login_firefighter(username: str, password: str, db: Session) -> str:
        repo = AuthRepositoryPG(db)

        user = repo.get_by_username_and_role(username, "firefighter")
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        password = _validate_password(password)
        if not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return create_access_token({"sub": username, "role": "firefighter"})
