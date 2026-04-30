from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.core.firebase import get_firestore_client


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class FirestoreStore:
    def __init__(self):
        self.db = get_firestore_client()

    def get_user(self, username: str, role: str) -> Optional[dict[str, Any]]:
        docs = (
            self.db.collection("users")
            .where("username", "==", username)
            .where("role", "==", role)
            .limit(1)
            .stream()
        )
        for doc in docs:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            return data
        return None

    def create_user(self, username: str, hashed_password: str, role: str) -> dict[str, Any]:
        payload = {
            "username": username,
            "hashed_password": hashed_password,
            "role": role,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        ref = self.db.collection("users").document()
        ref.set(payload)
        payload["id"] = ref.id
        return payload

    def create_fire_scenario(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = payload.copy()
        body["created_at"] = _now_iso()
        body["updated_at"] = _now_iso()
        ref = self.db.collection("fire_scenarios").document()
        ref.set(body)
        body["id"] = ref.id
        return body

    def update_fire_scenario(self, scenario_id: str, patch: dict[str, Any]) -> None:
        patch = patch.copy()
        patch["updated_at"] = _now_iso()
        self.db.collection("fire_scenarios").document(str(scenario_id)).set(patch, merge=True)

    def get_fire_scenario(self, scenario_id: str) -> Optional[dict[str, Any]]:
        doc = self.db.collection("fire_scenarios").document(str(scenario_id)).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        data["id"] = doc.id
        return data

    def list_fire_scenarios(self, limit: int = 50) -> list[dict[str, Any]]:
        docs = (
            self.db.collection("fire_scenarios")
            .order_by("created_at", direction="DESCENDING")
            .limit(limit)
            .stream()
        )
        rows: list[dict[str, Any]] = []
        for doc in docs:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            rows.append(data)
        return rows

    def list_active_scenario_ids(self) -> list[str]:
        docs = self.db.collection("fire_scenarios").where("status", "==", "active").stream()
        return [doc.id for doc in docs]

    def create_spread_snapshot(self, scenario_id: str, payload: dict[str, Any]) -> None:
        body = payload.copy()
        body["scenario_id"] = str(scenario_id)
        body["created_at"] = _now_iso()
        self.db.collection("fire_scenarios").document(str(scenario_id)).collection("snapshots").add(body)

    def count_spread_snapshots(self, scenario_id: str) -> int:
        return len(
            list(self.db.collection("fire_scenarios").document(str(scenario_id)).collection("snapshots").stream())
        )

    def get_latest_spread_snapshot(self, scenario_id: str) -> Optional[dict[str, Any]]:
        docs = (
            self.db.collection("fire_scenarios")
            .document(str(scenario_id))
            .collection("snapshots")
            .order_by("step", direction="DESCENDING")
            .limit(1)
            .stream()
        )
        for doc in docs:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            return data
        return None

    def upsert_user_location(self, user_key: str, payload: dict[str, Any]) -> None:
        body = payload.copy()
        body["updated_at"] = _now_iso()
        self.db.collection("user_locations").document(str(user_key)).set(body, merge=True)

    def get_enabled_user_locations(self) -> list[dict[str, Any]]:
        docs = self.db.collection("user_locations").where("notifications_enabled", "==", True).stream()
        rows: list[dict[str, Any]] = []
        for doc in docs:
            data = doc.to_dict() or {}
            data["user_key"] = doc.id
            rows.append(data)
        return rows

    def create_alert(self, payload: dict[str, Any]) -> None:
        body = payload.copy()
        body["created_at"] = _now_iso()
        self.db.collection("spread_alerts").add(body)

    def get_latest_alert(self, scenario_id: str, user_key: str) -> Optional[dict[str, Any]]:
        docs = (
            self.db.collection("spread_alerts")
            .where("scenario_id", "==", str(scenario_id))
            .where("user_key", "==", str(user_key))
            .order_by("created_at", direction="DESCENDING")
            .limit(1)
            .stream()
        )
        for doc in docs:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            return data
        return None

    def list_alerts_for_user(self, user_key: str, limit: int = 20) -> list[dict[str, Any]]:
        docs = (
            self.db.collection("spread_alerts")
            .where("user_key", "==", str(user_key))
            .order_by("created_at", direction="DESCENDING")
            .limit(limit)
            .stream()
        )
        rows: list[dict[str, Any]] = []
        for doc in docs:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            rows.append(data)
        return rows

    # ---- pipelines ----
    def list_pipelines(self, username: str) -> list[dict[str, Any]]:
        docs = (
            self.db.collection("pipelines")
            .where("username", "==", username)
            .order_by("created_at", direction="DESCENDING")
            .stream()
        )
        rows: list[dict[str, Any]] = []
        for doc in docs:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            rows.append(data)
        return rows

    def create_pipeline(
        self,
        *,
        username: str,
        name: str,
        n: int,
        k: int,
        snapshot_json: Optional[str],
    ) -> dict[str, Any]:
        payload = {
            "username": username,
            "name": name,
            "n": n,
            "k": k,
            "snapshot_json": snapshot_json,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        ref = self.db.collection("pipelines").document()
        ref.set(payload)
        payload["id"] = ref.id
        return payload

    def get_pipeline(self, pipeline_id: str, username: str) -> Optional[dict[str, Any]]:
        doc = self.db.collection("pipelines").document(str(pipeline_id)).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        if data.get("username") != username:
            return None
        data["id"] = doc.id
        return data

    def delete_pipeline(self, pipeline_id: str, username: str) -> bool:
        doc = self.db.collection("pipelines").document(str(pipeline_id)).get()
        if not doc.exists:
            return False
        data = doc.to_dict() or {}
        if data.get("username") != username:
            return False
        doc.reference.delete()
        return True
