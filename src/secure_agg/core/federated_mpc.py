"""Federated-learning style secure MPC aggregation API."""

from __future__ import annotations

from dataclasses import dataclass

from secure_agg.constants import PARTY_COUNT, PARTY_IDS
from secure_agg.core.aggregation import (
    AggregationResult,
    aggregate_received_shares,
    reconstruct_aggregation,
)
from secure_agg.crypto.fixed_point import encode_vector
from secure_agg.crypto.secret_sharing import split_vector
from secure_agg.exceptions import (
    DimensionMismatchError,
    InvalidShareError,
    UnknownParticipantError,
)


@dataclass(frozen=True)
class EncryptedModelParameters:
    """A participant's encoded model parameters split into MPC share vectors."""

    party_id: str
    share_vectors: list[list[int]]


def encrypt_model_parameters(
    party_id: str,
    parameter_values: list[float],
) -> EncryptedModelParameters:
    """Encode and split one participant's model parameters into secret shares."""
    if party_id not in PARTY_IDS:
        raise UnknownParticipantError(f"unknown party_id: {party_id}")

    encoded = encode_vector(parameter_values)
    return EncryptedModelParameters(
        party_id=party_id,
        share_vectors=split_vector(encoded, party_count=PARTY_COUNT),
    )


def aggregate_encrypted_model_parameters(
    encrypted_parameters: list[EncryptedModelParameters],
) -> AggregationResult:
    """Aggregate encrypted participant parameters and recover sum and average."""
    _validate_encrypted_parameters(encrypted_parameters)

    aggregate_shares: list[list[int]] = []
    for receiver_index in range(PARTY_COUNT):
        received_shares = [
            sender_parameters.share_vectors[receiver_index]
            for sender_parameters in encrypted_parameters
        ]
        aggregate_shares.append(aggregate_received_shares(received_shares))

    return reconstruct_aggregation(aggregate_shares, participant_count=PARTY_COUNT)


def _validate_encrypted_parameters(
    encrypted_parameters: list[EncryptedModelParameters],
) -> None:
    if len(encrypted_parameters) != PARTY_COUNT:
        raise InvalidShareError("exactly three encrypted model parameter sets are required")

    party_ids = [parameters.party_id for parameters in encrypted_parameters]
    if set(party_ids) != set(PARTY_IDS) or len(party_ids) != len(set(party_ids)):
        raise UnknownParticipantError("encrypted parameters must come from P1, P2, and P3")

    expected_length: int | None = None
    for parameters in encrypted_parameters:
        if len(parameters.share_vectors) != PARTY_COUNT:
            raise InvalidShareError("each encrypted parameter set must contain three share vectors")
        for share_vector in parameters.share_vectors:
            if expected_length is None:
                expected_length = len(share_vector)
            elif len(share_vector) != expected_length:
                raise DimensionMismatchError("encrypted share vectors must have the same length")
