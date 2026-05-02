from typing import Generator
from app.core.database import SessionLocal

def get_db() -> Generator[object, None, None]:
    yield SessionLocal()
