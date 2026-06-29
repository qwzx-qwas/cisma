"""Run a minimal federated learning demo with secure MPC aggregation."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from secure_agg.core.federated_learning import (
    TrainingExample,
    mean_squared_error,
    run_secure_federated_training,
)


def demo_datasets() -> dict[str, list[TrainingExample]]:
    """Create three non-IID local datasets for y = 2x + 1."""
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


def main() -> None:
    """Run and print the federated learning demo."""
    datasets = demo_datasets()
    initial_parameters = [0.0, 0.0]
    initial_loss = mean_squared_error(initial_parameters, datasets)
    history = run_secure_federated_training(
        initial_parameters,
        datasets,
        rounds=8,
        learning_rate=0.03,
        local_epochs=10,
    )

    print("=" * 60)
    print("Federated Learning + Secure MPC Aggregation Demo")
    print("=" * 60)
    print("Clients: P1, P2, P3")
    print("Model: y = weight * x + bias")
    print("Aggregation: additive secret sharing over encrypted model parameters")
    print(f"Initial parameters: {initial_parameters}")
    print(f"Initial loss: {initial_loss:.6f}")
    print()
    for result in history:
        weight, bias = result.global_parameters
        print(
            f"Round {result.round_index}: "
            f"global_parameters=[{weight:.6f}, {bias:.6f}], "
            f"loss={result.loss:.6f}"
        )
    print()
    print(f"Final parameters: {history[-1].global_parameters}")
    print(f"Result: {'PASS' if history[-1].loss < initial_loss else 'FAIL'}")
    print("=" * 60)

    if history[-1].loss >= initial_loss:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
