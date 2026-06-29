import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from secure_agg.core.aggregation import plaintext_average, plaintext_sum
from secure_agg.core.federated_mpc import (
    EncryptedModelParameters,
    aggregate_encrypted_model_parameters,
    encrypt_model_parameters,
)
from secure_agg.exceptions import DimensionMismatchError, InvalidShareError, UnknownParticipantError


def test_federated_mpc_aggregation_matches_plaintext_baseline() -> None:
    vectors = {
        "P1": [1.25, -2.0, 3.5],
        "P2": [2.75, 4.0, -1.5],
        "P3": [-3.0, 1.0, 2.0],
    }
    encrypted = [
        encrypt_model_parameters(party_id, values)
        for party_id, values in vectors.items()
    ]

    result = aggregate_encrypted_model_parameters(encrypted)

    plain_vectors = list(vectors.values())
    assert result.sum_values == pytest.approx(plaintext_sum(plain_vectors), abs=1e-5)
    assert result.average_values == pytest.approx(plaintext_average(plain_vectors), abs=1e-5)
    assert result.participant_count == 3


def test_federated_mpc_rejects_missing_participant() -> None:
    encrypted = [
        encrypt_model_parameters("P1", [1.0]),
        encrypt_model_parameters("P2", [2.0]),
    ]

    with pytest.raises(InvalidShareError):
        aggregate_encrypted_model_parameters(encrypted)


def test_federated_mpc_rejects_duplicate_participant() -> None:
    encrypted = [
        encrypt_model_parameters("P1", [1.0]),
        encrypt_model_parameters("P1", [2.0]),
        encrypt_model_parameters("P3", [3.0]),
    ]

    with pytest.raises(UnknownParticipantError):
        aggregate_encrypted_model_parameters(encrypted)


def test_federated_mpc_rejects_dimension_mismatch() -> None:
    encrypted = [
        encrypt_model_parameters("P1", [1.0, 2.0]),
        encrypt_model_parameters("P2", [2.0]),
        encrypt_model_parameters("P3", [3.0]),
    ]

    with pytest.raises(DimensionMismatchError):
        aggregate_encrypted_model_parameters(encrypted)


def test_federated_mpc_rejects_malformed_encrypted_parameters() -> None:
    encrypted = [
        EncryptedModelParameters("P1", [[1], [2], [3]]),
        EncryptedModelParameters("P2", [[4], [5], [6]]),
        EncryptedModelParameters("P3", [[7], [8]]),
    ]

    with pytest.raises(InvalidShareError):
        aggregate_encrypted_model_parameters(encrypted)
