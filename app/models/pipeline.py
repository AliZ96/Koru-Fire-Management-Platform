from sqlalchemy import String, DateTime, Text, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserPipeline(Base):
    __tablename__ = "user_pipelines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    n: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    k: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
