import json
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


# ── ModelParameters dataclass ────────────────────────────────────────

def test_create_parameters() -> None:
    params = ModelParameters(values=[1.0, 2.0, 3.0], shape=(3,))
    assert params.values == [1.0, 2.0, 3.0]
    assert params.shape == (3,)
    assert params.names is None


def test_create_with_names() -> None:
    params = ModelParameters(values=[1.0, 2.0], shape=(2,), names=("weight", "bias"))
    assert params.names == ("weight", "bias")


def test_frozen_dataclass() -> None:
    params = ModelParameters(values=[1.0], shape=(1,))
    with pytest.raises(AttributeError):
        params.values = [2.0]  # type: ignore


# ── Load / Save ──────────────────────────────────────────────────────

def test_load_and_save_basic_parameter_file(tmp_path: Path) -> None:
    source = tmp_path / "params.json"
    source.write_text('{"shape": [3], "values": [1.0, -2.5, 0.0]}', encoding="utf-8")

    parameters = load_parameters(str(source))
    target = tmp_path / "out.json"
    save_parameters(parameters, str(target))

    assert parameters == ModelParameters(values=[1.0, -2.5, 0.0], shape=(3,))
    assert load_parameters(str(target)) == parameters


def test_load_extended_format(tmp_path: Path) -> None:
    """测试加载扩展格式（多层参数字典）"""
    data = {"layers": {"layer1.weight": [1.0, 2.0], "layer1.bias": [0.1], "layer2.weight": [3.0, 4.0]}}
    source = tmp_path / "extended.json"
    source.write_text(json.dumps(data), encoding="utf-8")

    params = load_parameters(str(source))
    assert params.values == [1.0, 2.0, 0.1, 3.0, 4.0]
    assert params.shape == (5,)


def test_load_nonexistent_file() -> None:
    with pytest.raises(FileNotFoundError):
        load_parameters("/nonexistent/path.json")


def test_load_invalid_json(tmp_path: Path) -> None:
    source = tmp_path / "bad.json"
    source.write_text("not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_parameters(str(source))


def test_load_rejects_shape_mismatch(tmp_path: Path) -> None:
    source = tmp_path / "bad.json"
    source.write_text('{"shape": [2], "values": [1.0]}', encoding="utf-8")
    with pytest.raises(DimensionMismatchError):
        load_parameters(str(source))


def test_save_with_names(tmp_path: Path) -> None:
    params = ModelParameters(values=[1.0, 2.0], shape=(2,), names=("weight",))
    target = tmp_path / "out.json"
    save_parameters(params, str(target))

    with open(target) as f:
        data = json.load(f)
    assert "names" in data
    assert data["names"] == ["weight"]


# ── Flatten / Restore ────────────────────────────────────────────────

def test_flatten_and_restore_parameter_groups() -> None:
    flat, metadata = flatten_parameters({"w": [1.0, 2.0], "b": [-0.5]})
    assert flat == [1.0, 2.0, -0.5]
    assert restore_parameters(flat, metadata) == {"w": [1.0, 2.0], "b": [-0.5]}


def test_flatten_multi_groups() -> None:
    groups = {"layer1.weight": [1.0, 2.0], "layer1.bias": [0.5], "layer2.weight": [3.0, 4.0, 5.0]}
    flat, metadata = flatten_parameters(groups)
    assert flat == [1.0, 2.0, 0.5, 3.0, 4.0, 5.0]
    assert metadata["names"] == ["layer1.weight", "layer1.bias", "layer2.weight"]


def test_flatten_empty_groups() -> None:
    with pytest.raises(ValueError):
        flatten_parameters({})


def test_restore_roundtrip() -> None:
    original = {"a": [1.0, 2.0], "b": [3.0], "c": [4.0, 5.0, 6.0]}
    flat, metadata = flatten_parameters(original)
    restored = restore_parameters(flat, metadata)
    assert restored == original


# ── validate_same_shape ──────────────────────────────────────────────

def test_validate_same_shape_passes() -> None:
    validate_same_shape([
        ModelParameters([1.0, 2.0], (2,)),
        ModelParameters([3.0, 4.0], (2,)),
        ModelParameters([5.0, 6.0], (2,)),
    ])


def test_validate_same_shape_rejects_different_lengths() -> None:
    with pytest.raises(DimensionMismatchError):
        validate_same_shape([
            ModelParameters([1.0, 2.0], (2,)),
            ModelParameters([1.0], (1,)),
        ])


def test_validate_same_shape_empty_list() -> None:
    """空参数列表 — 明确定义行为"""
    validate_same_shape([])


def test_validate_same_shape_single_element() -> None:
    validate_same_shape([ModelParameters([1.0], (1,))])
