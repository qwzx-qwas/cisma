"""Model parameter loading, saving, flattening, and shape validation."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any

from secure_agg.exceptions import DimensionMismatchError


@dataclass(frozen=True)
class ModelParameters:
    """Flat model parameters plus shape metadata."""

    values: list[float]
    shape: tuple[int, ...]
    names: tuple[str, ...] | None = None


def _coerce_float_list(values: object) -> list[float]:
    if not isinstance(values, list):
        raise ValueError("values must be a list")

    converted: list[float] = []
    for value in values:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("parameter values must be numeric")
        float_value = float(value)
        if not math.isfinite(float_value):
            raise ValueError("parameter values must be finite")
        converted.append(float_value)
    return converted


def _coerce_shape(shape: object) -> tuple[int, ...]:
    if not isinstance(shape, list):
        raise ValueError("shape must be a list")
    if not shape:
        raise ValueError("shape must not be empty")

    converted: list[int] = []
    for dimension in shape:
        if not isinstance(dimension, int) or isinstance(dimension, bool):
            raise ValueError("shape dimensions must be integers")
        if dimension < 0:
            raise ValueError("shape dimensions must be non-negative")
        converted.append(dimension)
    return tuple(converted)


def _shape_size(shape: tuple[int, ...]) -> int:
    size = 1
    for dimension in shape:
        size *= dimension
    return size


def _validate_model_parameters(parameters: ModelParameters) -> None:
    if _shape_size(parameters.shape) != len(parameters.values):
        raise DimensionMismatchError("shape does not match values length")
    if parameters.names is not None and len(parameters.names) == 0:
        raise ValueError("names must be non-empty when provided")


def load_parameters(path: str) -> ModelParameters:
    """Read model parameters from a JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("parameter file must contain a JSON object")

    if "layers" in data:
        layers = data["layers"]
        if not isinstance(layers, dict):
            raise ValueError("layers must be a JSON object")
        flat_values, metadata = flatten_parameters(layers)
        parameters = ModelParameters(
            values=flat_values,
            shape=(len(flat_values),),
            names=tuple(metadata["names"]),
        )
        _validate_model_parameters(parameters)
        return parameters

    values = _coerce_float_list(data.get("values"))
    shape = _coerce_shape(data.get("shape"))
    names: tuple[str, ...] | None = None
    if "names" in data:
        if not isinstance(data["names"], list) or not all(
            isinstance(name, str) for name in data["names"]
        ):
            raise ValueError("names must be a list of strings")
        names = tuple(data["names"])

    parameters = ModelParameters(values=values, shape=shape, names=names)
    _validate_model_parameters(parameters)
    return parameters


def save_parameters(
    parameters: ModelParameters,
    path: str,
) -> None:
    """Write model parameters to a JSON file."""
    _validate_model_parameters(parameters)
    output: dict[str, Any] = {
        "shape": list(parameters.shape),
        "values": list(parameters.values),
    }
    if parameters.names is not None:
        output["names"] = list(parameters.names)

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def flatten_parameters(
    parameter_groups: dict[str, list[float]],
) -> tuple[list[float], dict]:
    """Flatten named parameter groups and return restoration metadata."""
    if not isinstance(parameter_groups, dict) or not parameter_groups:
        raise ValueError("parameter_groups must be a non-empty dict")

    flat_values: list[float] = []
    entries: list[dict[str, int | str]] = []
    for name, values in parameter_groups.items():
        if not isinstance(name, str) or not name:
            raise ValueError("parameter group names must be non-empty strings")
        group_values = _coerce_float_list(values)
        entries.append(
            {
                "name": name,
                "start": len(flat_values),
                "length": len(group_values),
            }
        )
        flat_values.extend(group_values)

    metadata = {
        "names": [entry["name"] for entry in entries],
        "entries": entries,
        "total_length": len(flat_values),
    }
    return flat_values, metadata


def restore_parameters(
    flat_values: list[float],
    metadata: dict,
) -> dict[str, list[float]]:
    """Restore named parameter groups from flat values and metadata."""
    values = _coerce_float_list(flat_values)
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be a dict")
    if metadata.get("total_length") != len(values):
        raise DimensionMismatchError("metadata length does not match flat values")

    restored: dict[str, list[float]] = {}
    entries = metadata.get("entries")
    if not isinstance(entries, list):
        raise ValueError("metadata entries must be a list")

    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("metadata entry must be a dict")
        name = entry.get("name")
        start = entry.get("start")
        length = entry.get("length")
        if not isinstance(name, str) or not isinstance(start, int) or not isinstance(length, int):
            raise ValueError("metadata entry has invalid fields")
        if start < 0 or length < 0 or start + length > len(values):
            raise DimensionMismatchError("metadata entry is outside flat values")
        restored[name] = list(values[start : start + length])

    return restored


def validate_same_shape(
    parameter_sets: list[ModelParameters],
) -> None:
    """Validate that all participants submitted parameters with the same shape."""
    if not parameter_sets:
        return

    expected_shape = parameter_sets[0].shape
    expected_length = len(parameter_sets[0].values)
    for parameters in parameter_sets:
        _validate_model_parameters(parameters)
        if parameters.shape != expected_shape or len(parameters.values) != expected_length:
            raise DimensionMismatchError("all parameter sets must have the same shape")
