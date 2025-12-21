from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class AuthRepositoryPG:
    def __init__(self, db: Session):
        self.db = db

    def get_by_username_and_role(self, username: str, role: str) -> User | None:
        stmt = select(User).where(User.username == username, User.role == role)
        return self.db.execute(stmt).scalars().first()

    def create_user(self, username: str, hashed_password: str, role: str) -> User:
        user = User(username=username, hashed_password=hashed_password, role=role)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
