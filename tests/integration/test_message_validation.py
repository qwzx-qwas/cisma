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


def test_round_create_request_validates_constants() -> None:
    request = RoundCreateRequest(
        round_id="r1",
        participant_ids=["P1", "P2", "P3"],
        vector_length=2,
        scale=SCALE,
        modulus=PRIME,
    )

    assert request.model_dump()["round_id"] == "r1"


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


def test_result_message_requires_matching_result_lengths() -> None:
    with pytest.raises(ValueError):
        AggregationResultMessage(
            round_id="r1",
            sum_values=[1.0],
            average_values=[],
            participant_count=3,
            status="completed",
        )
