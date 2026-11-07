"""Redis-backed idempotency service for critical write operations."""
import hashlib
import json
from typing import Any
import uuid
from redis.asyncio import Redis
from app.config import get_settings
from app.core.exceptions import ConflictError

settings = get_settings()


class IdempotencyService:
    """Manages idempotent request tokens, payload hashing, and response replay via Redis."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    @staticmethod
    def hash_payload(data: bytes | str) -> str:
        """Compute SHA-256 hash of the request body bytes."""
        raw_bytes = data.encode("utf-8") if isinstance(data, str) else data
        return hashlib.sha256(raw_bytes).hexdigest()

    def _make_key(self, user_id: uuid.UUID, idempotency_key: str) -> str:
        return f"idempotency:{user_id}:{idempotency_key}"

    async def get_recorded_response(
        self,
        user_id: uuid.UUID,
        idempotency_key: str,
        current_hash: str,
    ) -> dict[str, Any] | None:
        """
        Check if an idempotency key has already been processed.
        If hash matches: return cached response dict {"status_code": int, "body": dict}.
        If hash differs: raise ConflictError (409) indicating key reuse with mutated payload.
        """
        key = self._make_key(user_id, idempotency_key)
        try:
            stored_val = await self.redis.get(key)
        except Exception:
            return None

        if stored_val is None:
            return None

        data = json.loads(stored_val)
        if data.get("request_hash") != current_hash:
            raise ConflictError(
                message="Idempotency-Key reuse violation: request body does not match original request."
            )
        return data

    async def store_response(
        self,
        user_id: uuid.UUID,
        idempotency_key: str,
        request_hash: str,
        status_code: int,
        response_body: dict[str, Any],
        ttl_seconds: int | None = None,
    ) -> None:
        """Persist successful execution response under idempotency key."""
        key = self._make_key(user_id, idempotency_key)
        ttl = ttl_seconds or settings.IDEMPOTENCY_KEY_TTL_SECONDS
        payload = {
            "request_hash": request_hash,
            "status_code": status_code,
            "response_body": response_body,
        }
        try:
            await self.redis.set(key, json.dumps(payload), ex=ttl)
        except Exception:
            pass
