from __future__ import annotations

from app.services.firestore_store import FirestoreStore


class AuthRepositoryPG:
    """
    Compat sınıf adı korunur, fakat persistence Firestore'dur.
    """
    def __init__(self, db=None):
        self.store = FirestoreStore()

    def get_by_username_and_role(self, username: str, role: str):
        return self.store.get_user(username, role)

    def create_user(self, username: str, hashed_password: str, role: str):
        return self.store.create_user(username, hashed_password, role)
