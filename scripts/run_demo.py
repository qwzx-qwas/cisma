"""Run an end-to-end secure aggregation demo against local services."""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from secure_agg.constants import PRIME, SCALE
from secure_agg.core.aggregation import plaintext_average, plaintext_sum
from secure_agg.core.model_params import load_parameters, validate_same_shape


PARTY_CONFIGS = [
    ROOT / "configs" / "party_p1.json",
    ROOT / "configs" / "party_p2.json",
    ROOT / "configs" / "party_p3.json",
]
COORDINATOR_URL = "http://127.0.0.1:8000"
PARTY_URLS = {
    "P1": "http://127.0.0.1:8101",
    "P2": "http://127.0.0.1:8102",
    "P3": "http://127.0.0.1:8103",
}


def request_json(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Send one JSON request using the standard library."""
    body = json.dumps(payload or {}).encode("utf-8") if method == "POST" else None
    request = Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=10.0) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"{url} returned non-object JSON")
    return data


def ensure_online() -> None:
    """Check that all local services are reachable."""
    urls = [f"{COORDINATOR_URL}/health"] + [
        f"{base_url}/health" for base_url in PARTY_URLS.values()
    ]
    for url in urls:
        try:
            request_json("GET", url)
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(
                f"service is not reachable at {url}; run python scripts/start_all.py first"
            ) from exc


def load_demo_parameters():
    """Load demo parameters for baseline comparison only."""
    configs = [json.loads(path.read_text(encoding="utf-8")) for path in PARTY_CONFIGS]
    parameters = [
        load_parameters(str(ROOT / config["parameter_file"]))
        for config in configs
    ]
    validate_same_shape(parameters)
    return parameters


def poll_result(round_id: str, timeout_seconds: float = 10.0) -> dict[str, Any]:
    """Poll the coordinator until a completed result is available."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        result = request_json("GET", f"{COORDINATOR_URL}/rounds/{round_id}/result")
        if result.get("status") == "completed":
            return result
        time.sleep(0.2)
    raise TimeoutError("aggregation result was not completed in time")


def main() -> None:
    """Run the complete demo flow and print the comparison."""
    print("=" * 50)
    print("Secure Aggregation Demo")
    print("=" * 50)

    ensure_online()
    parameters = load_demo_parameters()
    vector_length = len(parameters[0].values)

    print()
    print("Participants: P1, P2, P3")
    print(f"Vector length: {vector_length}")
    print()

    print("[1/5] Creating aggregation round... ", end="", flush=True)
    round_response = request_json(
        "POST",
        f"{COORDINATOR_URL}/rounds",
        {
            "participant_ids": ["P1", "P2", "P3"],
            "vector_length": vector_length,
            "scale": SCALE,
            "modulus": PRIME,
        },
    )
    round_id = str(round_response["round_id"])
    print("OK")
    print(f"Round ID: {round_id}")

    print("[2/5] Distributing secret shares... ", end="", flush=True)
    for party_id, base_url in PARTY_URLS.items():
        request_json("POST", f"{base_url}/rounds/{round_id}/distribute")
    print("OK")

    print("[3/5] Computing local aggregate shares... ", end="", flush=True)
    for party_id, base_url in PARTY_URLS.items():
        request_json("POST", f"{base_url}/rounds/{round_id}/aggregate")
    print("OK")

    print("[4/5] Reconstructing aggregation result... ", end="", flush=True)
    result = poll_result(round_id)
    print("OK")

    print("[5/5] Comparing with plaintext baseline... ", end="", flush=True)
    parameter_vectors = [parameters_item.values for parameters_item in parameters]
    plain_sum = plaintext_sum(parameter_vectors)
    plain_average = plaintext_average(parameter_vectors)
    secure_sum = [float(value) for value in result["sum_values"]]
    secure_average = [float(value) for value in result["average_values"]]
    errors = [
        abs(left - right)
        for left, right in zip(secure_average, plain_average)
    ] + [
        abs(left - right)
        for left, right in zip(secure_sum, plain_sum)
    ]
    max_error = max(errors, default=0.0)
    passed = math.isfinite(max_error) and max_error <= 1e-5
    print("OK")

    print()
    print(f"Secure sum:     {secure_sum}")
    print(f"Secure average: {secure_average}")
    print(f"Plain average:  {plain_average}")
    print(f"Maximum error:  {max_error:.6f}")
    print()
    print(f"Result: {'PASS' if passed else 'FAIL'}")
    print("=" * 50)

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
