"""Message schemas and digest validation for secure aggregation."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from secure_agg.constants import PRIME, SCALE

try:  # pragma: no cover - exercised when pydantic is installed.
    from pydantic import BaseModel as _PydanticBaseModel
except ModuleNotFoundError:  # pragma: no cover - fallback is covered by tests here.
    _PydanticBaseModel = None


def compute_payload_digest(payload: list[int]) -> str:
    """Compute the SHA-256 digest for a payload vector."""
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_non_empty_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _validate_vector_length(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("vector_length must be a non-negative integer")
    return value


def _validate_payload(payload: object, vector_length: int) -> list[int]:
    if not isinstance(payload, list):
        raise ValueError("payload must be a list")
    if len(payload) != vector_length:
        raise ValueError("payload length must match vector_length")
    for value in payload:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("payload values must be integers")
        if value < 0 or value >= PRIME:
            raise ValueError("payload values must be finite-field elements")
    return list(payload)


def _validate_digest(payload: list[int], digest: object) -> str:
    digest_text = _validate_non_empty_text(digest, "digest")
    if digest_text != compute_payload_digest(payload):
        raise ValueError("digest does not match payload")
    return digest_text


def _validate_participant_ids(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError("participant_ids must be a non-empty list")
    participant_ids = [_validate_non_empty_text(item, "participant_id") for item in value]
    if len(set(participant_ids)) != len(participant_ids):
        raise ValueError("participant_ids must be unique")
    return participant_ids


if _PydanticBaseModel is not None:

    class _MessageBase(_PydanticBaseModel):
        def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
            """Return model data with a Pydantic-version-stable method."""
            parent_dump = getattr(super(), "model_dump", None)
            if parent_dump is not None:
                return parent_dump(*args, **kwargs)
            return self.dict(*args, **kwargs)

else:

    class _MessageBase:
        def __init__(self, **data: Any) -> None:
            annotations = getattr(self, "__annotations__", {})
            extra = set(data) - set(annotations)
            missing = set(annotations) - set(data)
            if extra:
                raise ValueError(f"unexpected fields: {sorted(extra)}")
            if missing:
                raise ValueError(f"missing fields: {sorted(missing)}")
            for name in annotations:
                setattr(self, name, data[name])
            self._validate()

        def dict(self) -> dict[str, Any]:
            """Return model data as a plain dictionary."""
            return {
                name: getattr(self, name)
                for name in getattr(self, "__annotations__", {})
            }

        def model_dump(self) -> dict[str, Any]:
            """Return model data as a plain dictionary."""
            return self.dict()


class RoundCreateRequest(_MessageBase):
    """Request to create a new aggregation round."""

    round_id: str
    participant_ids: list[str]
    vector_length: int
    scale: int
    modulus: int

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._validate()

    def _validate(self) -> None:
        self.round_id = _validate_non_empty_text(self.round_id, "round_id")
        self.participant_ids = _validate_participant_ids(self.participant_ids)
        self.vector_length = _validate_vector_length(self.vector_length)
        if self.scale != SCALE:
            raise ValueError("scale does not match project constant")
        if self.modulus != PRIME:
            raise ValueError("modulus does not match project constant")


class ShareMessage(_MessageBase):
    """Secret share sent from one participant to another."""

    round_id: str
    sender_id: str
    receiver_id: str
    vector_length: int
    payload: list[int]
    digest: str

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._validate()

    def _validate(self) -> None:
        self.round_id = _validate_non_empty_text(self.round_id, "round_id")
        self.sender_id = _validate_non_empty_text(self.sender_id, "sender_id")
        self.receiver_id = _validate_non_empty_text(self.receiver_id, "receiver_id")
        self.vector_length = _validate_vector_length(self.vector_length)
        self.payload = _validate_payload(self.payload, self.vector_length)
        self.digest = _validate_digest(self.payload, self.digest)


class AggregateShareMessage(_MessageBase):
    """Aggregate share sent from one participant to the coordinator."""

    round_id: str
    party_id: str
    vector_length: int
    payload: list[int]
    digest: str

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._validate()

    def _validate(self) -> None:
        self.round_id = _validate_non_empty_text(self.round_id, "round_id")
        self.party_id = _validate_non_empty_text(self.party_id, "party_id")
        self.vector_length = _validate_vector_length(self.vector_length)
        self.payload = _validate_payload(self.payload, self.vector_length)
        self.digest = _validate_digest(self.payload, self.digest)


class AggregationResultMessage(_MessageBase):
    """Decoded aggregation result returned by the coordinator."""

    round_id: str
    sum_values: list[float]
    average_values: list[float]
    participant_count: int
    status: str

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._validate()

    def _validate(self) -> None:
        self.round_id = _validate_non_empty_text(self.round_id, "round_id")
        self.status = _validate_non_empty_text(self.status, "status")
        if not isinstance(self.participant_count, int) or self.participant_count <= 0:
            raise ValueError("participant_count must be positive")
        if not isinstance(self.sum_values, list) or not isinstance(self.average_values, list):
            raise ValueError("result values must be lists")
        if len(self.sum_values) != len(self.average_values):
            raise ValueError("sum_values and average_values must have the same length")
        self.sum_values = [float(value) for value in self.sum_values]
        self.average_values = [float(value) for value in self.average_values]
