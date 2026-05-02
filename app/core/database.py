"""
Legacy DB module kept for import compatibility after Firebase cutover.
"""

from app.core.firebase import get_firestore_client


def SessionLocal():
    """
    Compat function name. Returns Firestore client instead of SQLAlchemy session.
    """
    return get_firestore_client()