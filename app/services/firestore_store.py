from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from google.api_core.exceptions import FailedPrecondition, ResourceExhausted
from google.cloud.firestore import FieldFilter

from app.core.firebase import get_firestore_client


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


FIRESTORE_SAFE_FIELD_BYTES = 900_000
_HEAVY_SNAPSHOT_KEYS = {"road_geometry", "geometry", "polyline", "coordinates"}


def _json_size(value: str) -> int:
    return len(value.encode("utf-8"))


def _strip_heavy_route_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_heavy_route_data(item)
            for key, item in value.items()
            if key not in _HEAVY_SNAPSHOT_KEYS
        }
    if isinstance(value, list):
        return [_strip_heavy_route_data(item) for item in value]
    return value


def _remove_ga20(snapshot: Any) -> Any:
    if not isinstance(snapshot, dict):
        return snapshot
    compact = dict(snapshot)
    optimization = compact.get("optimization")
    if isinstance(optimization, dict):
        optimization = dict(optimization)
        optimization.pop("GA20", None)
        compact["optimization"] = optimization
    compact.pop("ga20_routes", None)
    return compact


def compact_snapshot_json(snapshot_json: Optional[str]) -> Optional[str]:
    if not snapshot_json or _json_size(snapshot_json) <= FIRESTORE_SAFE_FIELD_BYTES:
        return snapshot_json
    try:
        snapshot = json.loads(snapshot_json)
    except (TypeError, ValueError):
        return None

    for candidate in (
        _remove_ga20(snapshot),
        _strip_heavy_route_data(_remove_ga20(snapshot)),
    ):
        compact_json = json.dumps(candidate, ensure_ascii=False, separators=(",", ":"))
        if _json_size(compact_json) <= FIRESTORE_SAFE_FIELD_BYTES:
            return compact_json

    minimal = {
        key: snapshot.get(key)
        for key in ("pipeline_points", "stations", "n", "k", "sa_routes", "ga_routes")
        if isinstance(snapshot, dict) and key in snapshot
    }
    compact_json = json.dumps(minimal, ensure_ascii=False, separators=(",", ":"))
    return compact_json if _json_size(compact_json) <= FIRESTORE_SAFE_FIELD_BYTES else None


class FirestoreStore:
    def __init__(self):
        self.db = get_firestore_client()

    def get_user(self, username: str, role: str) -> Optional[dict[str, Any]]:
        normalized_role = str(role or "user").lower()
        try:
            docs = (
                self.db.collection("users")
                .where(filter=FieldFilter("username", "==", username))
                .stream()
            )
            for doc in docs:
                data = doc.to_dict() or {}
                if str(data.get("role") or "").lower() != normalized_role:
                    continue
                data["id"] = doc.id
                return data
        except (FailedPrecondition, ResourceExhausted):
            pass
        try:
            for doc in self.db.collection("users").stream():
                data = doc.to_dict() or {}
                if data.get("username") != username:
                    continue
                if str(data.get("role") or "").lower() != normalized_role:
                    continue
                data["id"] = doc.id
                return data
        except ResourceExhausted:
            pass
        return None

    def create_user(self, username: str, hashed_password: str, role: str) -> dict[str, Any]:
        normalized_role = str(role or "user").lower()
        payload = {
            "username": username,
            "hashed_password": hashed_password,
            "role": normalized_role,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        ref = self.db.collection("users").document()
        ref.set(payload)
        payload["id"] = ref.id
        return payload

    def upsert_user_profile(
        self,
        *,
        username: str,
        role: str,
        firebase_uid: str | None = None,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        normalized_role = str(role or "user").lower()
        existing = None
        same_username_doc = None
        try:
            docs = (
                self.db.collection("users")
                .where(filter=FieldFilter("username", "==", username))
                .stream()
            )
            for doc in docs:
                if same_username_doc is None:
                    same_username_doc = doc
                data = doc.to_dict() or {}
                if str(data.get("role") or "").lower() == normalized_role:
                    existing = doc
                    break
        except FailedPrecondition:
            # Bileşik index yoksa: tüm users üzerinden filtrele (küçük koleksiyonlar için uygun).
            for doc in self.db.collection("users").stream():
                data = doc.to_dict() or {}
                if data.get("username") != username:
                    continue
                if same_username_doc is None:
                    same_username_doc = doc
                if str(data.get("role") or "").lower() == normalized_role:
                    existing = doc
                    break

        if existing is None:
            # Legacy USER/user farkında aynı username için tek kaydı normalize ederek tekrar kullanım.
            existing = same_username_doc

        patch = {
            "updated_at": _now_iso(),
            "auth_provider": "firebase",
            "role": normalized_role,
        }
        if firebase_uid:
            patch["firebase_uid"] = firebase_uid
        if display_name:
            patch["display_name"] = display_name

        if existing is not None:
            existing.reference.set(patch, merge=True)
            data = (existing.reference.get().to_dict() or {})
            data["id"] = existing.id
            return data

        payload = {
            "username": username,
            "hashed_password": "FIREBASE_AUTH_MANAGED",
            "role": normalized_role,
            "created_at": _now_iso(),
            **patch,
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
        try:
            docs = self.db.collection("fire_scenarios").where(filter=FieldFilter("status", "==", "active")).stream()
            return [doc.id for doc in docs]
        except ResourceExhausted:
            return []

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
        docs = self.db.collection("user_locations").where(
            filter=FieldFilter("notifications_enabled", "==", True)
        ).stream()
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
            .where(filter=FieldFilter("scenario_id", "==", str(scenario_id)))
            .where(filter=FieldFilter("user_key", "==", str(user_key)))
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
            .where(filter=FieldFilter("user_key", "==", str(user_key)))
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
        rows: list[dict[str, Any]] = []
        try:
            docs = (
                self.db.collection("pipelines")
                .where(filter=FieldFilter("username", "==", username))
                .stream()
            )
            for doc in docs:
                data = doc.to_dict() or {}
                data["id"] = doc.id
                rows.append(data)
        except FailedPrecondition:
            # Fallback: index gerektiren sorgu hatasında tüm koleksiyondan filtrele.
            docs = self.db.collection("pipelines").stream()
            for doc in docs:
                data = doc.to_dict() or {}
                if data.get("username") != username:
                    continue
                data["id"] = doc.id
                rows.append(data)
        rows.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        return rows

    def create_pipeline(
        self,
        *,
        username: str,
        name: str,
        n: int,
        k: int,
        pop: Optional[int] = None,
        iter: Optional[int] = None,
        temp: Optional[int] = None,
        snapshot_json: Optional[str] = None,
    ) -> dict[str, Any]:
        snapshot_json = compact_snapshot_json(snapshot_json)
        payload = {
            "username": username,
            "name": name,
            "n": n,
            "k": k,
            "pop": pop,
            "iter": iter,
            "temp": temp,
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
