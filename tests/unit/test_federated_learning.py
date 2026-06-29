import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from secure_agg.core.federated_learning import (
    TrainingExample,
    mean_squared_error,
    run_secure_federated_round,
    run_secure_federated_training,
    train_local_linear_model,
)
from secure_agg.exceptions import DimensionMismatchError, UnknownParticipantError


def _datasets() -> dict[str, list[TrainingExample]]:
    return {
        "P1": [
            TrainingExample([0.0], 1.0),
            TrainingExample([1.0], 3.0),
            TrainingExample([2.0], 5.0),
        ],
        "P2": [
            TrainingExample([3.0], 7.0),
            TrainingExample([4.0], 9.0),
            TrainingExample([5.0], 11.0),
        ],
        "P3": [
            TrainingExample([-1.0], -1.0),
            TrainingExample([-2.0], -3.0),
            TrainingExample([6.0], 13.0),
        ],
    }


def test_local_linear_training_reduces_loss() -> None:
    examples = _datasets()["P1"]
    initial = [0.0, 0.0]
    trained = train_local_linear_model(initial, examples, learning_rate=0.05, epochs=20)

    initial_loss = mean_squared_error(initial, {"P1": examples})
    trained_loss = mean_squared_error(trained, {"P1": examples})

    assert trained_loss < initial_loss


def test_secure_federated_round_averages_local_models() -> None:
    datasets = _datasets()
    initial = [0.0, 0.0]

    result = run_secure_federated_round(
        initial,
        datasets,
        learning_rate=0.03,
        local_epochs=10,
    )

    expected = [
        sum(parameters[index] for parameters in result.local_parameters.values()) / 3
        for index in range(len(initial))
    ]
    assert result.global_parameters == pytest.approx(expected, abs=1e-5)


def test_secure_federated_training_reduces_global_loss() -> None:
    datasets = _datasets()
    initial = [0.0, 0.0]
    initial_loss = mean_squared_error(initial, datasets)

    history = run_secure_federated_training(
        initial,
        datasets,
        rounds=8,
        learning_rate=0.03,
        local_epochs=10,
    )

    assert len(history) == 8
    assert history[-1].loss < initial_loss
    assert history[-1].global_parameters[0] == pytest.approx(2.0, abs=0.5)


def test_secure_federated_training_requires_three_clients() -> None:
    datasets = _datasets()
    del datasets["P3"]

    with pytest.raises(UnknownParticipantError):
        run_secure_federated_training([0.0, 0.0], datasets)


def test_local_training_rejects_feature_mismatch() -> None:
    with pytest.raises(DimensionMismatchError):
        train_local_linear_model(
            [0.0, 0.0],
            [
                TrainingExample([1.0], 3.0),
                TrainingExample([1.0, 2.0], 5.0),
            ],
        )
