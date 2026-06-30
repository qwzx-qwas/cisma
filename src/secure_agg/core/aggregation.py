"""Core aggregation helpers for plaintext baselines and secret shares."""

from __future__ import annotations

from dataclasses import dataclass

from secure_agg.constants import PARTY_COUNT, PRIME
from secure_agg.crypto.fixed_point import decode_vector
from secure_agg.crypto.field import vector_mod_add
from secure_agg.crypto.secret_sharing import reconstruct_vector
from secure_agg.exceptions import DimensionMismatchError, InvalidShareError


@dataclass(frozen=True)
class AggregationResult:
    """Decoded secure aggregation result and its encoded sum."""

    encoded_sum: list[int]
    sum_values: list[float]
    average_values: list[float]
    participant_count: int


def _validate_same_length(vectors: list[list[object]], label: str) -> int:
    if not vectors:
        raise InvalidShareError(f"{label} must not be empty")

    expected_length = len(vectors[0])
    if any(len(vector) != expected_length for vector in vectors):
        raise DimensionMismatchError(f"{label} must have the same length")
    return expected_length


def plaintext_sum(
    parameter_vectors: list[list[float]],
) -> list[float]:
    """Compute an element-wise plaintext sum baseline."""
    if not parameter_vectors:
        return []

    _validate_same_length(parameter_vectors, "parameter vectors")
    if not parameter_vectors[0]:
        return []

    return [
        sum(vector[index] for vector in parameter_vectors)
        for index in range(len(parameter_vectors[0]))
    ]


def plaintext_average(
    parameter_vectors: list[list[float]],
) -> list[float]:
    """Compute an element-wise plaintext average baseline."""
    if not parameter_vectors:
        return []

    summed = plaintext_sum(parameter_vectors)
    return [value / len(parameter_vectors) for value in summed]


def aggregate_received_shares(
    received_shares: list[list[int]],
    prime: int = PRIME,
) -> list[int]:
    """Aggregate the three received share vectors for one party."""
    if len(received_shares) != PARTY_COUNT:
        raise InvalidShareError("exactly three received share vectors are required")
    _validate_same_length(received_shares, "received shares")

    aggregate = [0 for _ in range(len(received_shares[0]))]
    for share in received_shares:
        aggregate = vector_mod_add(aggregate, share, prime)
    return aggregate


def reconstruct_aggregation(
    aggregate_shares: list[list[int]],
    participant_count: int = PARTY_COUNT,
) -> AggregationResult:
    """Recover sum and average values from aggregate share vectors."""
    if participant_count <= 0:
        raise ValueError("participant_count must be positive")

    _validate_same_length(aggregate_shares, "aggregate shares")
    if len(aggregate_shares) != participant_count:
        raise InvalidShareError("all aggregate shares must be received before recovery")

    encoded_sum = reconstruct_vector(aggregate_shares, PRIME)
    sum_values = decode_vector(encoded_sum)
    average_values = [value / participant_count for value in sum_values]
    return AggregationResult(
        encoded_sum=encoded_sum,
        sum_values=sum_values,
        average_values=average_values,
        participant_count=participant_count,
    )
