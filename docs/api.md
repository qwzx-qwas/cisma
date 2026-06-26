# Core API

This document describes the pure local API implemented by member two. The HTTP
layer should call these functions instead of reimplementing aggregation logic.

## Model Parameters

- `load_parameters(path: str) -> ModelParameters`
- `save_parameters(parameters: ModelParameters, path: str) -> None`
- `flatten_parameters(parameter_groups: dict[str, list[float]]) -> tuple[list[float], dict]`
- `restore_parameters(flat_values: list[float], metadata: dict) -> dict[str, list[float]]`
- `validate_same_shape(parameter_sets: list[ModelParameters]) -> None`

The basic JSON format is:

```json
{
  "shape": [3],
  "values": [1.0, 2.0, 3.0]
}
```

`shape` must match the number of values. Parameter values must be finite
numbers.

## Aggregation

- `plaintext_sum(parameter_vectors: list[list[float]]) -> list[float]`
- `plaintext_average(parameter_vectors: list[list[float]]) -> list[float]`
- `aggregate_received_shares(received_shares: list[list[int]], prime: int = PRIME) -> list[int]`
- `reconstruct_aggregation(aggregate_shares: list[list[int]], participant_count: int = 3) -> AggregationResult`

`aggregate_received_shares` requires exactly three received share vectors.
`reconstruct_aggregation` requires all aggregate shares before decoding the
result. Both functions reject mismatched vector lengths.

The implementation calls member-one finite-field and sharing helpers:
`decode_vector`, `reconstruct_vector`, and `vector_mod_add`. Local workflows
should use member-one `encode_vector` and `split_vector` before submitting
shares.

## Round State

`AggregationRound` records one round's participant IDs, vector length, received
shares, aggregate shares, status, and error message.

It rejects unknown participants, duplicate submissions, wrong vector lengths,
writes after completion, and writes after failure. Call `complete()` only after
all aggregate shares are present.

## Messages

The schema module exposes:

- `RoundCreateRequest`
- `ShareMessage`
- `AggregateShareMessage`
- `AggregationResultMessage`
- `compute_payload_digest(payload: list[int]) -> str`

`digest` is a SHA-256 checksum over the canonical JSON payload vector. It only
detects accidental or simple message corruption; it is not authentication and
must not be documented as a signature.

The project expects Pydantic for runtime schema validation in the HTTP layer.
The local test environment can use the built-in fallback if Pydantic is not
installed.
