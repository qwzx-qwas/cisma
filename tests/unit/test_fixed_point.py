import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from secure_agg.constants import PRIME, SCALE
from secure_agg.crypto.fixed_point import (
    decode_int,
    decode_vector,
    encode_float,
    encode_vector,
)
from secure_agg.exceptions import EncodingError, EncodingOverflowError


@pytest.mark.parametrize("value", [0.0, 1.25, -2.5, 3.75, -0.000001])
def test_encode_decode_float_round_trips_with_fixed_point_tolerance(value: float) -> None:
    assert decode_int(encode_float(value)) == pytest.approx(value, abs=1e-6)


def test_encode_vector_and_decode_vector_preserve_input_and_values() -> None:
    values = [1.25, -2.5, 3.75]
    encoded = encode_vector(values)
    decoded = decode_vector(encoded)

    assert decoded == pytest.approx(values, abs=1e-6)
    assert values == [1.25, -2.5, 3.75]


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_encode_float_rejects_nan_and_infinity(value: float) -> None:
    with pytest.raises(EncodingError):
        encode_float(value)


def test_encode_float_rejects_values_outside_safe_signed_range() -> None:
    too_large = ((PRIME - 1) // 2 + 1) / SCALE
    with pytest.raises(EncodingOverflowError):
        encode_float(too_large)


def test_decode_int_interprets_upper_half_as_negative() -> None:
    assert decode_int(PRIME - SCALE) == pytest.approx(-1.0, abs=1e-6)
