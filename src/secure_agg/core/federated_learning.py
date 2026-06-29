"""Minimal federated learning loop with secure MPC aggregation."""

from __future__ import annotations

from dataclasses import dataclass

from secure_agg.constants import PARTY_IDS
from secure_agg.core.federated_mpc import (
    aggregate_encrypted_model_parameters,
    encrypt_model_parameters,
)
from secure_agg.exceptions import DimensionMismatchError, UnknownParticipantError


@dataclass(frozen=True)
class TrainingExample:
    """One supervised training sample for linear regression."""

    features: list[float]
    target: float


@dataclass(frozen=True)
class FederatedRoundResult:
    """Result of one federated learning round."""

    round_index: int
    global_parameters: list[float]
    local_parameters: dict[str, list[float]]
    loss: float


def predict(parameters: list[float], features: list[float]) -> float:
    """Predict with a linear model whose last parameter is the bias."""
    if len(parameters) != len(features) + 1:
        raise DimensionMismatchError("parameter length must equal feature length plus bias")
    return sum(weight * value for weight, value in zip(parameters[:-1], features)) + parameters[-1]


def mean_squared_error(
    parameters: list[float],
    datasets: dict[str, list[TrainingExample]],
) -> float:
    """Compute mean squared error over all client datasets."""
    total_loss = 0.0
    total_count = 0
    for examples in datasets.values():
        for example in examples:
            error = predict(parameters, example.features) - example.target
            total_loss += error * error
            total_count += 1
    if total_count == 0:
        raise ValueError("at least one training example is required")
    return total_loss / total_count


def train_local_linear_model(
    initial_parameters: list[float],
    examples: list[TrainingExample],
    learning_rate: float = 0.05,
    epochs: int = 20,
) -> list[float]:
    """Train one client's linear model using batch gradient descent."""
    if not examples:
        raise ValueError("local dataset must not be empty")
    if learning_rate <= 0:
        raise ValueError("learning_rate must be positive")
    if epochs <= 0:
        raise ValueError("epochs must be positive")

    feature_count = len(examples[0].features)
    if len(initial_parameters) != feature_count + 1:
        raise DimensionMismatchError("initial parameters do not match local data")
    if any(len(example.features) != feature_count for example in examples):
        raise DimensionMismatchError("all training examples must have the same feature length")

    parameters = list(initial_parameters)
    for _ in range(epochs):
        gradients = [0.0 for _ in parameters]
        for example in examples:
            error = predict(parameters, example.features) - example.target
            for index, feature_value in enumerate(example.features):
                gradients[index] += 2.0 * error * feature_value
            gradients[-1] += 2.0 * error

        scale = learning_rate / len(examples)
        parameters = [
            value - scale * gradient
            for value, gradient in zip(parameters, gradients)
        ]
    return parameters


def run_secure_federated_round(
    global_parameters: list[float],
    datasets: dict[str, list[TrainingExample]],
    learning_rate: float = 0.05,
    local_epochs: int = 20,
    round_index: int = 1,
) -> FederatedRoundResult:
    """Train locally on each client and aggregate models with secret sharing."""
    _validate_federated_datasets(datasets)

    local_parameters = {
        party_id: train_local_linear_model(
            global_parameters,
            datasets[party_id],
            learning_rate=learning_rate,
            epochs=local_epochs,
        )
        for party_id in PARTY_IDS
    }
    encrypted_parameters = [
        encrypt_model_parameters(party_id, local_parameters[party_id])
        for party_id in PARTY_IDS
    ]
    aggregation_result = aggregate_encrypted_model_parameters(encrypted_parameters)
    next_global_parameters = aggregation_result.average_values
    return FederatedRoundResult(
        round_index=round_index,
        global_parameters=next_global_parameters,
        local_parameters=local_parameters,
        loss=mean_squared_error(next_global_parameters, datasets),
    )


def run_secure_federated_training(
    initial_parameters: list[float],
    datasets: dict[str, list[TrainingExample]],
    rounds: int = 5,
    learning_rate: float = 0.05,
    local_epochs: int = 20,
) -> list[FederatedRoundResult]:
    """Run multiple federated learning rounds with secure MPC aggregation."""
    if rounds <= 0:
        raise ValueError("rounds must be positive")

    history: list[FederatedRoundResult] = []
    global_parameters = list(initial_parameters)
    for round_index in range(1, rounds + 1):
        result = run_secure_federated_round(
            global_parameters,
            datasets,
            learning_rate=learning_rate,
            local_epochs=local_epochs,
            round_index=round_index,
        )
        history.append(result)
        global_parameters = result.global_parameters
    return history


def _validate_federated_datasets(
    datasets: dict[str, list[TrainingExample]],
) -> None:
    if set(datasets) != set(PARTY_IDS):
        raise UnknownParticipantError("datasets must be provided for P1, P2, and P3")

    expected_feature_count: int | None = None
    for party_id in PARTY_IDS:
        examples = datasets[party_id]
        if not examples:
            raise ValueError("each client dataset must not be empty")
        for example in examples:
            if expected_feature_count is None:
                expected_feature_count = len(example.features)
            elif len(example.features) != expected_feature_count:
                raise DimensionMismatchError("all clients must use the same feature length")
