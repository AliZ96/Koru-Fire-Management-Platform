from fastapi import HTTPException

from app.core.config import settings
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
    def resolve_jwt_role_for_firebase_email(email: str) -> str:
        """Firebase e-postası için JWT rolü: ADMIN_EMAILS veya Firestore'da admin kaydı."""
        email = (email or "").strip().lower()
        if not email:
            return "user"
        if email in settings.admin_emails_list:
            return "admin"
        store = FirestoreStore()
        if store.get_user(email, "admin"):
            return "admin"
        return "user"

    @staticmethod
    def login_personnel_firebase(email: str, password: str) -> str:
        """Yetkili personel: Firebase e-posta/şifre + Firestore'da admin rolü zorunlu."""
        email = (email or "").strip().lower()
        if not email:
            raise HTTPException(status_code=400, detail="E-posta zorunlu.")
        _validate_password(password)
        FirebaseIdentityService.sign_in_with_email_password(email, password)
        
        # Check hardcoded whitelist first (no Firestore quota used)
        if email in settings.admin_emails_list:
            return create_access_token({"sub": email, "email": email, "role": "admin"})
            
        store = FirestoreStore()
        if not store.get_user(email, "admin"):
            raise HTTPException(
                status_code=403,
                detail="Yetkili giriş için hesabın Firestore'da admin rolü ile tanımlı olması gerekir. (Quota uyarısı alıyorsanız ADMIN_EMAILS listesine ekleyin)",
            )
        return create_access_token({"sub": email, "email": email, "role": "admin"})

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
        try:
            repo = AuthRepositoryPG(db)
        except Exception:
            raise HTTPException(status_code=503, detail="Storage service unavailable")

        existing = repo.get_by_username_and_role(username, "user")
        if existing:
            raise HTTPException(status_code=400, detail="User already exists")

        password = _validate_password(password)
        hashed = hash_password(password)

        repo.create_user(username, hashed, "user")
        return create_access_token({"sub": username, "role": "user"})

    @staticmethod
    def login_user(username: str, password: str, db=None) -> str:
        password = _validate_password(password)
        
        # Try to lookup user in local store (optional)
        repo = None
        user = None
        try:
            repo = AuthRepositoryPG(db)
            user = repo.get_by_username_and_role(username, "user")
        except Exception:
            # Firestore unavailable — skip local lookup
            pass
        
        # If user found locally and password matches, return token
        if user:
            user_hash = str(user.get("hashed_password") or user.get("password_hash") or "")
            if verify_password(password, user_hash):
                return create_access_token({"sub": username, "role": "user"})
        
        # Fallback: Firebase email/password login (always available)
        try:
            firebase_payload = FirebaseIdentityService.sign_in_with_email_password(username, password)
            firebase_email = str(firebase_payload.get("email") or username)
            firebase_uid = str(firebase_payload.get("localId") or "")
            
            # Try to save user to store (optional)
            if repo:
                try:
                    existing = repo.get_by_username_and_role(firebase_email, "user")
                    if not existing:
                        repo.create_user(firebase_email, hash_password(password), "user")
                except Exception:
                    pass
            
            return create_access_token(
                {
                    "sub": firebase_email,
                    "role": "user",
                    "auth_provider": "firebase_password",
                    "firebase_uid": firebase_uid,
                }
            )
        except Exception as e:
            # Firebase auth failed
            raise HTTPException(status_code=401, detail="Invalid credentials")

    @staticmethod
    def register_firefighter(username: str, password: str, db=None) -> str:
        try:
            repo = AuthRepositoryPG(db)
        except Exception:
            raise HTTPException(status_code=503, detail="Authentication backend unavailable")

        existing = repo.get_by_username_and_role(username, "firefighter")
        if existing:
            raise HTTPException(status_code=400, detail="User already exists")

        password = _validate_password(password)
        hashed = hash_password(password)

        repo.create_user(username, hashed, "firefighter")
        return create_access_token({"sub": username, "role": "firefighter"})

    @staticmethod
    def login_firefighter(username: str, password: str, db=None) -> str:
        try:
            repo = AuthRepositoryPG(db)
        except Exception:
            raise HTTPException(status_code=503, detail="Authentication backend unavailable")

        user = repo.get_by_username_and_role(username, "firefighter")
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        password = _validate_password(password)
        user_hash = str(user.get("hashed_password") or user.get("password_hash") or "")
        if not verify_password(password, user_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return create_access_token({"sub": username, "role": "firefighter"})
