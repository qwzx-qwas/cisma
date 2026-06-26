"""Coordinator HTTP service for secure aggregation rounds."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import uuid

from secure_agg.constants import PARTY_COUNT, PRIME, SCALE
from secure_agg.core.aggregation import reconstruct_aggregation
from secure_agg.core.round_state import AggregationRound, RoundStatus
from secure_agg.exceptions import InvalidRoundStateError
from secure_agg.network.client import post_json
from secure_agg.network.http_utils import HttpError, read_json, send_error_json, send_json
from secure_agg.schemas.messages import (
    AggregateShareMessage,
    AggregationResultMessage,
    RoundCreateRequest,
)


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CoordinatorConfig:
    """Runtime configuration for the coordinator service."""

    host: str
    port: int
    participant_ids: tuple[str, ...]
    party_urls: dict[str, str]


class CoordinatorState:
    """In-memory coordinator state."""

    def __init__(self, config: CoordinatorConfig) -> None:
        self.config = config
        self.rounds: dict[str, AggregationRound] = {}
        self.results: dict[str, AggregationResultMessage] = {}

    async def create_round(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a coordinator round and notify all participant services."""
        request_data = dict(payload)
        request_data.setdefault("round_id", str(uuid.uuid4()))
        request_data.setdefault("participant_ids", list(self.config.participant_ids))
        request_data.setdefault("scale", SCALE)
        request_data.setdefault("modulus", PRIME)
        request = RoundCreateRequest(**request_data)
        if tuple(request.participant_ids) != self.config.participant_ids:
            raise InvalidRoundStateError("participant_ids do not match coordinator config")

        existing = self.rounds.get(request.round_id)
        if existing is not None:
            return self.round_status(request.round_id)

        self.rounds[request.round_id] = AggregationRound(
            round_id=request.round_id,
            participant_ids=tuple(request.participant_ids),
            vector_length=request.vector_length,
        )
        for party_id in request.participant_ids:
            await post_json(
                f"{self.config.party_urls[party_id].rstrip('/')}/rounds",
                request.model_dump(),
            )
        LOGGER.info(
            "round=%s coordinator created vector_length=%s",
            request.round_id,
            request.vector_length,
        )
        return self.round_status(request.round_id)

    def receive_aggregate_share(self, round_id: str, message: AggregateShareMessage) -> dict[str, Any]:
        """Validate and store one aggregate share, reconstructing when complete."""
        if message.round_id != round_id:
            raise InvalidRoundStateError("path round_id does not match message")
        round_state = self._round(round_id)
        if round_id in self.results:
            raise InvalidRoundStateError("round is already completed")
        round_state.add_aggregate_share(message.party_id, message.payload)
        LOGGER.info(
            "round=%s coordinator received_aggregate party=%s length=%s",
            round_id,
            message.party_id,
            message.vector_length,
        )

        if round_state.all_aggregate_shares_received():
            ordered = [
                round_state.aggregate_shares[party_id]
                for party_id in round_state.participant_ids
            ]
            result = reconstruct_aggregation(ordered, participant_count=PARTY_COUNT)
            message_result = AggregationResultMessage(
                round_id=round_id,
                sum_values=result.sum_values,
                average_values=result.average_values,
                participant_count=result.participant_count,
                status=RoundStatus.COMPLETED.value,
            )
            self.results[round_id] = message_result
            round_state.complete()
            LOGGER.info("round=%s coordinator completed", round_id)
        return self.round_status(round_id)

    def round_status(self, round_id: str) -> dict[str, Any]:
        """Return coordinator status or completed result."""
        round_state = self._round(round_id)
        result = self.results.get(round_id)
        if result is not None:
            return result.model_dump()
        return {
            "round_id": round_id,
            "status": round_state.status.value,
            "received_aggregate_from": sorted(round_state.aggregate_shares),
            "participant_count": len(round_state.participant_ids),
            "vector_length": round_state.vector_length,
            "error_message": round_state.error_message,
        }

    def _round(self, round_id: str) -> AggregationRound:
        round_state = self.rounds.get(round_id)
        if round_state is None:
            raise HttpError(404, "round not found")
        return round_state


def load_coordinator_config(path: str) -> CoordinatorConfig:
    """Load a coordinator config file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    party_urls = {str(key): str(value) for key, value in data["party_urls"].items()}
    participant_ids = tuple(str(item) for item in data.get("participant_ids", party_urls.keys()))
    return CoordinatorConfig(
        host=str(data.get("host", "127.0.0.1")),
        port=int(data.get("port", 8000)),
        participant_ids=participant_ids,
        party_urls=party_urls,
    )


def create_handler(state: CoordinatorState) -> type[BaseHTTPRequestHandler]:
    """Create a request handler class bound to a coordinator state object."""

    class CoordinatorHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            try:
                path = urlparse(self.path).path
                if path == "/health":
                    send_json(self, 200, {"role": "coordinator", "status": "ok"})
                    return
                parts = path.strip("/").split("/")
                if len(parts) == 3 and parts[0] == "rounds" and parts[2] == "result":
                    send_json(self, 200, state.round_status(parts[1]))
                    return
                raise HttpError(404, "not found")
            except Exception as exc:
                send_error_json(self, exc)

        def do_POST(self) -> None:
            try:
                path = urlparse(self.path).path
                payload = read_json(self)
                if path == "/rounds":
                    send_json(self, 200, asyncio.run(state.create_round(payload)))
                    return
                parts = path.strip("/").split("/")
                if len(parts) == 3 and parts[0] == "rounds" and parts[2] == "aggregate-shares":
                    message = AggregateShareMessage(**payload)
                    send_json(self, 200, state.receive_aggregate_share(parts[1], message))
                    return
                raise HttpError(404, "not found")
            except Exception as exc:
                send_error_json(self, exc)

        def log_message(self, format: str, *args: object) -> None:
            LOGGER.info("coordinator_http %s", format % args)

    return CoordinatorHandler


def create_server(config: CoordinatorConfig) -> ThreadingHTTPServer:
    """Create a coordinator HTTP server."""
    state = CoordinatorState(config)
    return ThreadingHTTPServer((config.host, config.port), create_handler(state))


def main(argv: list[str] | None = None) -> None:
    """Run the coordinator service from a JSON config."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/coordinator.json")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = load_coordinator_config(args.config)
    server = create_server(config)
    LOGGER.info("coordinator listening on %s:%s", config.host, config.port)
    server.serve_forever()
