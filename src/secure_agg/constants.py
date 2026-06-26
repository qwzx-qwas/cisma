"""Shared constants for secure aggregation."""

PRIME = (1 << 61) - 1
SCALE = 1_000_000
PARTY_COUNT = 3
PARTY_IDS = ("P1", "P2", "P3")
PARTY_TO_INDEX = {
    "P1": 0,
    "P2": 1,
    "P3": 2,
}
