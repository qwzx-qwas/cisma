"""Finite-field arithmetic helpers."""

from secure_agg.constants import PRIME
from secure_agg.exceptions import DimensionMismatchError


def normalize(value: int, prime: int = PRIME) -> int:
    """Normalize any integer into the finite-field range [0, prime)."""
    if prime <= 0:
        raise ValueError("prime must be positive")
    return value % prime


def mod_add(a: int, b: int, prime: int = PRIME) -> int:
    """Return the finite-field addition result."""
    return normalize(a + b, prime)


def mod_sub(a: int, b: int, prime: int = PRIME) -> int:
    """Return the finite-field subtraction result."""
    return normalize(a - b, prime)


def vector_mod_add(
    left: list[int],
    right: list[int],
    prime: int = PRIME,
) -> list[int]:
    """Add two integer vectors element by element in the finite field."""
    if len(left) != len(right):
        raise DimensionMismatchError("vectors must have the same length")
    return [mod_add(a, b, prime) for a, b in zip(left, right)]
