from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    @staticmethod
    def get_by_username(db: Session, username: str) -> User | None:
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def create(db: Session, username: str, hashed_password: str, role: str = "user") -> User:
        user = User(
            username=username,
            hashed_password=hashed_password,
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
