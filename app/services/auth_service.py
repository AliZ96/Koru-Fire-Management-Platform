from fastapi import HTTPException

from app.core.security import hash_password, verify_password, create_access_token
from app.repositories.auth_repo import AuthRepositoryPG
from app.services.firestore_store import FirestoreStore
from app.services.firebase_identity_service import FirebaseIdentityService


def _validate_password(password: str) -> str:
    password = (password or "").strip()
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Password too long (bcrypt limit 72 bytes)")
    return password


class AuthService:
    @staticmethod
    def sync_user_profile(
        *,
        username: str,
        role: str = "user",
        firebase_uid: str | None = None,
        display_name: str | None = None,
    ) -> dict:
        store = FirestoreStore()
        return store.upsert_user_profile(
            username=username,
            role=role,
            firebase_uid=firebase_uid,
            display_name=display_name,
        )

    @staticmethod
    def register_user(username: str, password: str, db=None) -> str:
        repo = AuthRepositoryPG(db)

        existing = repo.get_by_username_and_role(username, "user")
        if existing:
            raise HTTPException(status_code=400, detail="User already exists")

        password = _validate_password(password)
        hashed = hash_password(password)

        repo.create_user(username, hashed, "user")
        return create_access_token({"sub": username, "role": "user"})

    @staticmethod
    def login_user(username: str, password: str, db=None) -> str:
        repo = AuthRepositoryPG(db)
        password = _validate_password(password)
        user = repo.get_by_username_and_role(username, "user")
        user_hash = ""
        if user:
            user_hash = str(user.get("hashed_password") or user.get("password_hash") or "")
        if user and verify_password(password, user_hash):
            return create_access_token({"sub": username, "role": "user"})

        # Fallback: Firebase email/password login (Swagger ve frontend parity)
        firebase_payload = FirebaseIdentityService.sign_in_with_email_password(username, password)
        firebase_email = str(firebase_payload.get("email") or username)
        firebase_uid = str(firebase_payload.get("localId") or "")

        existing = repo.get_by_username_and_role(firebase_email, "user")
        if not existing:
            repo.create_user(firebase_email, hash_password(password), "user")

        return create_access_token(
            {
                "sub": firebase_email,
                "role": "user",
                "auth_provider": "firebase_password",
                "firebase_uid": firebase_uid,
            }
        )

    @staticmethod
    def register_firefighter(username: str, password: str, db=None) -> str:
        repo = AuthRepositoryPG(db)

        existing = repo.get_by_username_and_role(username, "firefighter")
        if existing:
            raise HTTPException(status_code=400, detail="User already exists")

        password = _validate_password(password)
        hashed = hash_password(password)

        repo.create_user(username, hashed, "firefighter")
        return create_access_token({"sub": username, "role": "firefighter"})

    @staticmethod
    def login_firefighter(username: str, password: str, db=None) -> str:
        repo = AuthRepositoryPG(db)

        user = repo.get_by_username_and_role(username, "firefighter")
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        password = _validate_password(password)
        user_hash = str(user.get("hashed_password") or user.get("password_hash") or "")
        if not verify_password(password, user_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return create_access_token({"sub": username, "role": "firefighter"})
