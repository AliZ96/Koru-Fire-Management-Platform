from app.services.firestore_store import FirestoreStore


class UserRepository:
    @staticmethod
    def get_by_username(db, username: str):
        store = FirestoreStore()
        docs = store.db.collection("users").where("username", "==", username).limit(1).stream()
        for doc in docs:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            return data
        return None

    @staticmethod
    def create(db, username: str, hashed_password: str, role: str = "user"):
        store = FirestoreStore()
        return store.create_user(username, hashed_password, role)
