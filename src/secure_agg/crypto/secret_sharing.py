"""Additive secret sharing over a finite field."""

import secrets

from secure_agg.constants import PARTY_COUNT, PRIME
from secure_agg.crypto.field import mod_add, mod_sub, normalize, vector_mod_add
from secure_agg.exceptions import DimensionMismatchError


def split_secret(
    secret: int,
    party_count: int = PARTY_COUNT,
    prime: int = PRIME,
) -> list[int]:
    """Split one finite-field integer into additive secret shares."""
    if party_count <= 0:
        raise ValueError("party_count must be positive")

    normalized_secret = normalize(secret, prime)
    shares = [secrets.randbelow(prime) for _ in range(party_count - 1)]
    running_sum = 0
    for share in shares:
        running_sum = mod_add(running_sum, share, prime)
    shares.append(mod_sub(normalized_secret, running_sum, prime))
    return shares


def reconstruct_secret(
    shares: list[int],
    prime: int = PRIME,
) -> int:
    """Recover one secret integer from additive shares."""
    result = 0
    for share in shares:
        result = mod_add(result, share, prime)
    return result


def split_vector(
    secret_vector: list[int],
    party_count: int = PARTY_COUNT,
    prime: int = PRIME,
) -> list[list[int]]:
    """Split a vector into per-party additive share vectors."""
    party_shares: list[list[int]] = [[] for _ in range(party_count)]
    for secret in secret_vector:
        shares = split_secret(secret, party_count, prime)
        for index, share in enumerate(shares):
            party_shares[index].append(share)
    return party_shares


def reconstruct_vector(
    share_vectors: list[list[int]],
    prime: int = PRIME,
) -> list[int]:
    """Recover a secret vector from multiple additive share vectors."""
    if not share_vectors:
        return []

    expected_length = len(share_vectors[0])
    if any(len(shares) != expected_length for shares in share_vectors):
        raise DimensionMismatchError("share vectors must have the same length")

    result = [0 for _ in range(expected_length)]
    for shares in share_vectors:
        result = vector_mod_add(result, shares, prime)
    return result
