import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from secure_agg.constants import PARTY_COUNT, PRIME
from secure_agg.crypto.fixed_point import decode_int, decode_vector, encode_float, encode_vector
from secure_agg.crypto.secret_sharing import (
    reconstruct_secret,
    reconstruct_vector,
    split_secret,
    split_vector,
)
from secure_agg.exceptions import DimensionMismatchError


def test_positive_integer_split_and_reconstruct() -> None:
    secret = 123_456
    shares = split_secret(secret)
    assert len(shares) == PARTY_COUNT
    assert reconstruct_secret(shares) == secret


def test_zero_split_and_reconstruct() -> None:
    assert reconstruct_secret(split_secret(0)) == 0


def test_negative_float_can_be_encoded_split_reconstructed_and_decoded() -> None:
    value = -2.5
    encoded = encode_float(value)
    reconstructed = reconstruct_secret(split_secret(encoded))
    assert decode_int(reconstructed) == pytest.approx(value, abs=1e-6)


def test_vector_split_and_reconstruct() -> None:
    values = [1.25, -2.5, 3.75]
    encoded = encode_vector(values)
    shares = split_vector(encoded)
    reconstructed = reconstruct_vector(shares)
    decoded = decode_vector(reconstructed)

    assert len(shares) == PARTY_COUNT
    assert all(len(share) == len(values) for share in shares)
    assert reconstructed == encoded
    assert decoded == pytest.approx(values, abs=1e-6)


def test_split_vector_supports_empty_vectors() -> None:
    assert split_vector([]) == [[], [], []]
    assert reconstruct_vector([[], [], []]) == []


def test_reconstruct_vector_rejects_dimension_mismatch() -> None:
    with pytest.raises(DimensionMismatchError):
        reconstruct_vector([[1, 2], [3]])


def test_secret_values_are_normalized_before_sharing() -> None:
    shares = split_secret(PRIME + 7)
    assert reconstruct_secret(shares) == 7
