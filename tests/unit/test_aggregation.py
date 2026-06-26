import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from secure_agg.constants import PARTY_COUNT
from secure_agg.core.aggregation import (
    aggregate_received_shares,
    plaintext_average,
    plaintext_sum,
    reconstruct_aggregation,
)
from secure_agg.crypto.fixed_point import encode_vector
from secure_agg.crypto.secret_sharing import split_vector
from secure_agg.exceptions import DimensionMismatchError, InvalidShareError


def _secure_aggregate(parameter_vectors: list[list[float]]):
    per_sender_shares = [split_vector(encode_vector(values)) for values in parameter_vectors]
    aggregate_shares = []
    for party_index in range(PARTY_COUNT):
        received = [sender_shares[party_index] for sender_shares in per_sender_shares]
        aggregate_shares.append(aggregate_received_shares(received))
    return reconstruct_aggregation(aggregate_shares)


def test_plaintext_sum_and_average() -> None:
    vectors = [[1.0, 2.0], [3.0, 4.0], [-1.0, 0.5]]

    assert plaintext_sum(vectors) == pytest.approx([3.0, 6.5])
    assert plaintext_average(vectors) == pytest.approx([1.0, 2.1666666667])


def test_secure_aggregation_matches_plaintext_baseline() -> None:
    vectors = [[1.0, 2.0, 3.0], [2.0, 4.0, 6.0], [3.0, 6.0, 9.0]]

    result = _secure_aggregate(vectors)

    assert result.sum_values == pytest.approx(plaintext_sum(vectors), abs=1e-5)
    assert result.average_values == pytest.approx(plaintext_average(vectors), abs=1e-5)
    assert result.participant_count == PARTY_COUNT


def test_secure_aggregation_handles_mixed_signs_and_decimals() -> None:
    vectors = [[-1.5, 2.25], [3.0, -4.5], [0.5, 1.25]]

    result = _secure_aggregate(vectors)

    assert result.sum_values == pytest.approx([2.0, -1.0], abs=1e-5)
    assert result.average_values == pytest.approx([0.666667, -0.333333], abs=1e-5)


def test_empty_vector_shares_are_supported() -> None:
    assert aggregate_received_shares([[], [], []]) == []
    result = reconstruct_aggregation([[], [], []])
    assert result.sum_values == []
    assert result.average_values == []


def test_dimension_mismatch_is_rejected() -> None:
    with pytest.raises(DimensionMismatchError):
        plaintext_sum([[1.0], [1.0, 2.0]])
    with pytest.raises(DimensionMismatchError):
        aggregate_received_shares([[1], [2, 3], [4]])


def test_incomplete_shares_are_rejected() -> None:
    with pytest.raises(InvalidShareError):
        aggregate_received_shares([[1], [2]])
    with pytest.raises(InvalidShareError):
        reconstruct_aggregation([[1], [2]])
