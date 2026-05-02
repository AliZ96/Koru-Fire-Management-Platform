from app.core.database import SessionLocal


def get_db():
    yield SessionLocal()