import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from secure_agg.constants import PRIME, SCALE
from secure_agg.schemas.messages import (
    AggregateShareMessage,
    AggregationResultMessage,
    RoundCreateRequest,
    ShareMessage,
    compute_payload_digest,
)


# ── RoundCreateRequest ───────────────────────────────────────────────

def test_round_create_request_validates_constants() -> None:
    request = RoundCreateRequest(
        round_id="r1",
        participant_ids=["P1", "P2", "P3"],
        vector_length=2,
        scale=SCALE,
        modulus=PRIME,
    )
    assert request.model_dump()["round_id"] == "r1"


def test_round_create_rejects_wrong_scale() -> None:
    with pytest.raises(ValueError):
        RoundCreateRequest(
            round_id="r1",
            participant_ids=["P1"],
            vector_length=1,
            scale=999,
            modulus=PRIME,
        )


def test_round_create_rejects_wrong_modulus() -> None:
    with pytest.raises(ValueError):
        RoundCreateRequest(
            round_id="r1",
            participant_ids=["P1"],
            vector_length=1,
            scale=SCALE,
            modulus=999,
        )


def test_round_create_empty_participants_rejected() -> None:
    with pytest.raises(ValueError):
        RoundCreateRequest(
            round_id="r1",
            participant_ids=[],
            vector_length=1,
            scale=SCALE,
            modulus=PRIME,
        )


# ── ShareMessage ─────────────────────────────────────────────────────

def test_share_message_accepts_valid_digest() -> None:
    payload = [1, 2, 3]
    message = ShareMessage(
        round_id="r1",
        sender_id="P1",
        receiver_id="P2",
        vector_length=3,
        payload=payload,
        digest=compute_payload_digest(payload),
    )
    assert message.payload == payload


def test_share_message_rejects_tampered_payload_digest() -> None:
    with pytest.raises(ValueError):
        ShareMessage(
            round_id="r1",
            sender_id="P1",
            receiver_id="P2",
            vector_length=3,
            payload=[1, 2, 99],
            digest=compute_payload_digest([1, 2, 3]),
        )


def test_share_message_empty_payload() -> None:
    msg = ShareMessage(
        round_id="r1",
        sender_id="P1",
        receiver_id="P2",
        vector_length=0,
        payload=[],
        digest=compute_payload_digest([]),
    )
    assert msg.payload == []


def test_share_message_missing_field_rejected() -> None:
    with pytest.raises((ValueError, TypeError)):
        ShareMessage(  # type: ignore
            round_id="r1",
            sender_id="P1",
            vector_length=3,
            payload=[1, 2, 3],
            digest="abc",
        )


def test_share_message_payload_out_of_range_rejected() -> None:
    with pytest.raises(ValueError):
        ShareMessage(
            round_id="r1",
            sender_id="P1",
            receiver_id="P2",
            vector_length=1,
            payload=[PRIME],
            digest="abc",
        )


# ── AggregateShareMessage ────────────────────────────────────────────

def test_aggregate_share_message_basic() -> None:
    payload = [100, 200, 300]
    msg = AggregateShareMessage(
        round_id="r1",
        party_id="P1",
        vector_length=3,
        payload=payload,
        digest=compute_payload_digest(payload),
    )
    assert msg.party_id == "P1"


def test_aggregate_share_message_rejects_vector_length_mismatch() -> None:
    payload = [1, 2]
    with pytest.raises(ValueError):
        AggregateShareMessage(
            round_id="r1",
            party_id="P1",
            vector_length=3,
            payload=payload,
            digest=compute_payload_digest(payload),
        )


def test_aggregate_share_message_rejects_bad_digest() -> None:
    with pytest.raises(ValueError):
        AggregateShareMessage(
            round_id="r1",
            party_id="P1",
            vector_length=2,
            payload=[1, 2],
            digest="badhash",
        )


# ── AggregationResultMessage ─────────────────────────────────────────

def test_aggregation_result_message_completed() -> None:
    msg = AggregationResultMessage(
        round_id="r1",
        sum_values=[6.0, 12.0],
        average_values=[2.0, 4.0],
        participant_count=3,
        status="completed",
    )
    assert msg.status == "completed"


def test_result_message_requires_matching_result_lengths() -> None:
    with pytest.raises(ValueError):
        AggregationResultMessage(
            round_id="r1",
            sum_values=[1.0],
            average_values=[],
            participant_count=3,
            status="completed",
        )


# ── compute_payload_digest ───────────────────────────────────────────

def test_digest_consistency() -> None:
    payload = [1, 2, 3, 1000, -5]
    d1 = compute_payload_digest(payload)
    d2 = compute_payload_digest(payload)
    assert d1 == d2


def test_digest_changes_with_payload() -> None:
    assert compute_payload_digest([1, 2, 3]) != compute_payload_digest([1, 2, 4])


def test_digest_is_sha256() -> None:
    digest = compute_payload_digest([1, 2, 3])
    assert isinstance(digest, str)
    assert len(digest) == 64
    int(digest, 16)


def test_digest_empty_list() -> None:
    assert len(compute_payload_digest([])) == 64
