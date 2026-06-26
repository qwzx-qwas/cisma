import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from secure_agg.core.model_params import (
    ModelParameters,
    flatten_parameters,
    load_parameters,
    restore_parameters,
    save_parameters,
    validate_same_shape,
)
from secure_agg.exceptions import DimensionMismatchError


def test_load_and_save_basic_parameter_file(tmp_path: Path) -> None:
    source = tmp_path / "params.json"
    source.write_text('{"shape": [3], "values": [1.0, -2.5, 0.0]}', encoding="utf-8")

    parameters = load_parameters(str(source))
    target = tmp_path / "out.json"
    save_parameters(parameters, str(target))

    assert parameters == ModelParameters(values=[1.0, -2.5, 0.0], shape=(3,))
    assert load_parameters(str(target)) == parameters


def test_flatten_and_restore_parameter_groups() -> None:
    flat, metadata = flatten_parameters({"w": [1.0, 2.0], "b": [-0.5]})

    assert flat == [1.0, 2.0, -0.5]
    assert restore_parameters(flat, metadata) == {"w": [1.0, 2.0], "b": [-0.5]}


def test_load_rejects_shape_mismatch(tmp_path: Path) -> None:
    source = tmp_path / "bad.json"
    source.write_text('{"shape": [2], "values": [1.0]}', encoding="utf-8")

    with pytest.raises(DimensionMismatchError):
        load_parameters(str(source))


def test_validate_same_shape_rejects_different_lengths() -> None:
    with pytest.raises(DimensionMismatchError):
        validate_same_shape(
            [
                ModelParameters([1.0, 2.0], (2,)),
                ModelParameters([1.0], (1,)),
            ]
        )
