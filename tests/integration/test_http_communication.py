import asyncio
import json
import socket
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from secure_agg.constants import PRIME, SCALE
from secure_agg.network.client import get_json, post_json
from secure_agg.network.coordinator_server import CoordinatorConfig, create_server as create_coordinator_server
from secure_agg.network.party_server import PartyConfig, create_server as create_party_server
from secure_agg.schemas.messages import compute_payload_digest


def _free_port() -> int:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])
    except PermissionError:
        pytest.skip("local sockets are not permitted in this sandbox")


class RunningServer:
    def __init__(self, server) -> None:
        self.server = server
        self.thread = threading.Thread(target=server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2.0)


def _write_params(path: Path, values: list[float]) -> None:
    path.write_text(
        json.dumps({"shape": [len(values)], "values": values}),
        encoding="utf-8",
    )


def test_http_three_party_round(tmp_path: Path) -> None:
    ports = {
        "coordinator": _free_port(),
        "P1": _free_port(),
        "P2": _free_port(),
        "P3": _free_port(),
    }
    party_urls = {
        party_id: f"http://127.0.0.1:{ports[party_id]}"
        for party_id in ("P1", "P2", "P3")
    }
    coordinator_url = f"http://127.0.0.1:{ports['coordinator']}"
    param_files = {
        "P1": tmp_path / "p1.json",
        "P2": tmp_path / "p2.json",
        "P3": tmp_path / "p3.json",
    }
    _write_params(param_files["P1"], [1.0, 2.0, 3.0])
    _write_params(param_files["P2"], [2.0, 4.0, 6.0])
    _write_params(param_files["P3"], [3.0, 6.0, 9.0])

    coordinator = create_coordinator_server(
        CoordinatorConfig(
            host="127.0.0.1",
            port=ports["coordinator"],
            participant_ids=("P1", "P2", "P3"),
            party_urls=party_urls,
        )
    )
    parties = [
        create_party_server(
            PartyConfig(
                party_id=party_id,
                host="127.0.0.1",
                port=ports[party_id],
                parameter_file=str(param_files[party_id]),
                coordinator_url=coordinator_url,
                party_urls=party_urls,
            )
        )
        for party_id in ("P1", "P2", "P3")
    ]

    with RunningServer(coordinator), RunningServer(parties[0]), RunningServer(parties[1]), RunningServer(parties[2]):
        round_response = asyncio.run(
            post_json(
                f"{coordinator_url}/rounds",
                {
                    "participant_ids": ["P1", "P2", "P3"],
                    "vector_length": 3,
                    "scale": SCALE,
                    "modulus": PRIME,
                },
            )
        )
        round_id = round_response["round_id"]
        for base_url in party_urls.values():
            asyncio.run(post_json(f"{base_url}/rounds/{round_id}/distribute", {}))
        for base_url in party_urls.values():
            asyncio.run(post_json(f"{base_url}/rounds/{round_id}/aggregate", {}))
        result = asyncio.run(get_json(f"{coordinator_url}/rounds/{round_id}/result"))

    assert result["status"] == "completed"
    assert result["sum_values"] == pytest.approx([6.0, 12.0, 18.0], abs=1e-5)
    assert result["average_values"] == pytest.approx([2.0, 4.0, 6.0], abs=1e-5)


def test_party_rejects_bad_digest(tmp_path: Path) -> None:
    port = _free_port()
    party_url = f"http://127.0.0.1:{port}"
    param_file = tmp_path / "p1.json"
    _write_params(param_file, [1.0])
    server = create_party_server(
        PartyConfig(
            party_id="P1",
            host="127.0.0.1",
            port=port,
            parameter_file=str(param_file),
            coordinator_url="http://127.0.0.1:9",
            party_urls={"P1": party_url, "P2": party_url, "P3": party_url},
        )
    )

    with RunningServer(server):
        asyncio.run(
            post_json(
                f"{party_url}/rounds",
                {
                    "round_id": "r1",
                    "participant_ids": ["P1", "P2", "P3"],
                    "vector_length": 1,
                    "scale": SCALE,
                    "modulus": PRIME,
                },
            )
        )
        with pytest.raises(Exception):
            asyncio.run(
                post_json(
                    f"{party_url}/rounds/r1/shares",
                    {
                        "round_id": "r1",
                        "sender_id": "P1",
                        "receiver_id": "P1",
                        "vector_length": 1,
                        "payload": [2],
                        "digest": compute_payload_digest([1]),
                    },
                )
            )
