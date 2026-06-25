"""Fixed-point encoding for floating-point model parameters."""

import math

from secure_agg.constants import PRIME, SCALE
from secure_agg.crypto.field import normalize
from secure_agg.exceptions import EncodingError, EncodingOverflowError


def _max_signed_value(prime: int) -> int:
    """Return the largest signed integer that can be decoded unambiguously."""
    if prime <= 2:
        raise ValueError("prime must be greater than 2")
    return (prime - 1) // 2


def encode_float(
    value: float,
    scale: int = SCALE,
    prime: int = PRIME,
) -> int:
    """Encode a finite float as a signed fixed-point field element."""
    if scale <= 0:
        raise ValueError("scale must be positive")
    if not math.isfinite(value):
        raise EncodingError("value must be finite")

    scaled = round(value * scale)
    max_abs = _max_signed_value(prime)
    if scaled < -max_abs or scaled > max_abs:
        raise EncodingOverflowError("scaled value exceeds the supported range")
    return normalize(scaled, prime)


def decode_int(
    value: int,
    scale: int = SCALE,
    prime: int = PRIME,
) -> float:
    """Decode a fixed-point field element back into a float."""
    if scale <= 0:
        raise ValueError("scale must be positive")

    normalized = normalize(value, prime)
    max_abs = _max_signed_value(prime)
    signed = normalized - prime if normalized > max_abs else normalized
    return signed / scale


def encode_vector(
    values: list[float],
    scale: int = SCALE,
    prime: int = PRIME,
) -> list[int]:
    """Encode a vector of finite floats into fixed-point field elements."""
    return [encode_float(value, scale, prime) for value in values]


def decode_vector(
    values: list[int],
    scale: int = SCALE,
    prime: int = PRIME,
) -> list[float]:
    """Decode a vector of fixed-point field elements into floats."""
    return [decode_int(value, scale, prime) for value in values]
