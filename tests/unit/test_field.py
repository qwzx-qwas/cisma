import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from secure_agg.constants import PRIME
from secure_agg.crypto.field import mod_add, mod_sub, normalize, vector_mod_add
from secure_agg.exceptions import DimensionMismatchError


def test_normalize_keeps_values_inside_field() -> None:
    assert normalize(0) == 0
    assert normalize(PRIME) == 0
    assert normalize(-1) == PRIME - 1
    assert 0 <= normalize(PRIME * 3 + 9) < PRIME


def test_mod_add_and_sub_wrap_in_field() -> None:
    assert mod_add(PRIME - 1, 2) == 1
    assert mod_sub(1, 2) == PRIME - 1


def test_vector_mod_add_supports_empty_vectors() -> None:
    assert vector_mod_add([], []) == []


def test_vector_mod_add_does_not_mutate_inputs() -> None:
    left = [PRIME - 1, 2]
    right = [2, 3]
    assert vector_mod_add(left, right) == [1, 5]
    assert left == [PRIME - 1, 2]
    assert right == [2, 3]


def test_vector_mod_add_rejects_dimension_mismatch() -> None:
    with pytest.raises(DimensionMismatchError):
        vector_mod_add([1, 2], [1])
