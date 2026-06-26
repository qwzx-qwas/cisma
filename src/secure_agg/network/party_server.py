"""Participant HTTP service for secure aggregation rounds."""

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

from secure_agg.constants import PARTY_IDS, PARTY_TO_INDEX
from secure_agg.core.aggregation import aggregate_received_shares
from secure_agg.core.model_params import load_parameters
from secure_agg.core.round_state import AggregationRound, RoundStatus
from secure_agg.crypto.fixed_point import encode_vector
from secure_agg.crypto.secret_sharing import split_vector
from secure_agg.exceptions import InvalidRoundStateError, UnknownParticipantError
from secure_agg.network.client import send_aggregate_share, send_share
from secure_agg.network.http_utils import HttpError, read_json, send_error_json, send_json
from secure_agg.schemas.messages import (
    AggregateShareMessage,
    RoundCreateRequest,
    ShareMessage,
    compute_payload_digest,
)


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PartyConfig:
    """Runtime configuration for one participant service."""

    party_id: str
    host: str
    port: int
    parameter_file: str
    coordinator_url: str
    party_urls: dict[str, str]


class PartyState:
    """In-memory participant state."""

    def __init__(self, config: PartyConfig) -> None:
        self.config = config
        self.rounds: dict[str, AggregationRound] = {}
        self.submitted_aggregate_rounds: set[str] = set()

    def create_round(self, request: RoundCreateRequest) -> dict[str, Any]:
        """Create or validate a local round."""
        if self.config.party_id not in request.participant_ids:
            raise UnknownParticipantError("party is not part of this round")
        existing = self.rounds.get(request.round_id)
        participant_ids = tuple(request.participant_ids)
        if existing is not None:
            if existing.participant_ids != participant_ids or existing.vector_length != request.vector_length:
                raise InvalidRoundStateError("round already exists with different metadata")
            return self.status(request.round_id)

        self.rounds[request.round_id] = AggregationRound(
            round_id=request.round_id,
            participant_ids=participant_ids,
            vector_length=request.vector_length,
        )
        LOGGER.info(
            "round=%s party=%s created vector_length=%s",
            request.round_id,
            self.config.party_id,
            request.vector_length,
        )
        return self.status(request.round_id)

    def receive_share(self, message: ShareMessage) -> dict[str, Any]:
        """Validate and store one incoming secret share."""
        if message.receiver_id != self.config.party_id:
            raise UnknownParticipantError("share receiver does not match this party")
        round_state = self._round(message.round_id)
        round_state.validate_round_id(message.round_id)
        round_state.add_received_share(message.sender_id, message.payload)
        LOGGER.info(
            "round=%s party=%s received_share sender=%s length=%s",
            message.round_id,
            self.config.party_id,
            message.sender_id,
            message.vector_length,
        )
        return self.status(message.round_id)

    async def distribute(self, round_id: str) -> dict[str, Any]:
        """Encode local parameters, split them, and send shares to all parties."""
        round_state = self._round(round_id)
        if round_state.status == RoundStatus.COMPLETED:
            raise InvalidRoundStateError("completed round cannot distribute shares")
        parameters = load_parameters(self.config.parameter_file)
        if len(parameters.values) != round_state.vector_length:
            raise InvalidRoundStateError("local parameter length does not match round")

        encoded = encode_vector(parameters.values)
        party_shares = split_vector(encoded)
        for receiver_id in round_state.participant_ids:
            share = party_shares[PARTY_TO_INDEX[receiver_id]]
            message = ShareMessage(
                round_id=round_id,
                sender_id=self.config.party_id,
                receiver_id=receiver_id,
                vector_length=round_state.vector_length,
                payload=share,
                digest=compute_payload_digest(share),
            )
            if receiver_id == self.config.party_id:
                self.receive_share(message)
            else:
                await send_share(self.config.party_urls[receiver_id], message)

        LOGGER.info(
            "round=%s party=%s distributed_shares length=%s",
            round_id,
            self.config.party_id,
            round_state.vector_length,
        )
        return self.status(round_id)

    async def aggregate(self, round_id: str) -> dict[str, Any]:
        """Compute and submit this party's local aggregate share."""
        round_state = self._round(round_id)
        if round_id in self.submitted_aggregate_rounds:
            raise InvalidRoundStateError("aggregate share already submitted")
        if not round_state.all_shares_received():
            raise InvalidRoundStateError("cannot aggregate before all shares are received")

        received = [
            round_state.received_shares[party_id]
            for party_id in round_state.participant_ids
        ]
        aggregate_share = aggregate_received_shares(received)
        message = AggregateShareMessage(
            round_id=round_id,
            party_id=self.config.party_id,
            vector_length=round_state.vector_length,
            payload=aggregate_share,
            digest=compute_payload_digest(aggregate_share),
        )
        await send_aggregate_share(self.config.coordinator_url, message)
        self.submitted_aggregate_rounds.add(round_id)
        LOGGER.info(
            "round=%s party=%s submitted_aggregate length=%s",
            round_id,
            self.config.party_id,
            round_state.vector_length,
        )
        return self.status(round_id)

    def status(self, round_id: str) -> dict[str, Any]:
        """Return redacted local round status."""
        round_state = self._round(round_id)
        return {
            "round_id": round_id,
            "party_id": self.config.party_id,
            "status": round_state.status.value,
            "received_from": sorted(round_state.received_shares),
            "submitted_aggregate": round_id in self.submitted_aggregate_rounds,
            "error_message": round_state.error_message,
        }

    def _round(self, round_id: str) -> AggregationRound:
        round_state = self.rounds.get(round_id)
        if round_state is None:
            raise HttpError(404, "round not found")
        return round_state


def load_party_config(path: str) -> PartyConfig:
    """Load a participant service config file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return PartyConfig(
        party_id=str(data["party_id"]),
        host=str(data.get("host", "127.0.0.1")),
        port=int(data["port"]),
        parameter_file=str(data["parameter_file"]),
        coordinator_url=str(data["coordinator_url"]),
        party_urls={str(key): str(value) for key, value in data["party_urls"].items()},
    )


def create_handler(state: PartyState) -> type[BaseHTTPRequestHandler]:
    """Create a request handler class bound to a participant state object."""

    class PartyHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            try:
                path = urlparse(self.path).path
                if path == "/health":
                    send_json(self, 200, {"party_id": state.config.party_id, "status": "ok"})
                    return
                parts = path.strip("/").split("/")
                if len(parts) == 2 and parts[0] == "rounds":
                    send_json(self, 200, state.status(parts[1]))
                    return
                raise HttpError(404, "not found")
            except Exception as exc:
                send_error_json(self, exc)

        def do_POST(self) -> None:
            try:
                path = urlparse(self.path).path
                payload = read_json(self)
                if path == "/rounds":
                    request = RoundCreateRequest(**payload)
                    send_json(self, 200, state.create_round(request))
                    return

                parts = path.strip("/").split("/")
                if len(parts) == 3 and parts[0] == "rounds":
                    round_id = parts[1]
                    action = parts[2]
                    if action == "distribute":
                        send_json(self, 200, asyncio.run(state.distribute(round_id)))
                        return
                    if action == "shares":
                        message = ShareMessage(**payload)
                        if message.round_id != round_id:
                            raise InvalidRoundStateError("path round_id does not match message")
                        send_json(self, 200, state.receive_share(message))
                        return
                    if action == "aggregate":
                        send_json(self, 200, asyncio.run(state.aggregate(round_id)))
                        return
                raise HttpError(404, "not found")
            except Exception as exc:
                send_error_json(self, exc)

        def log_message(self, format: str, *args: object) -> None:
            LOGGER.info("party_http %s", format % args)

    return PartyHandler


def create_server(config: PartyConfig) -> ThreadingHTTPServer:
    """Create a participant HTTP server."""
    if config.party_id not in PARTY_IDS:
        raise UnknownParticipantError(f"unknown party_id: {config.party_id}")
    state = PartyState(config)
    return ThreadingHTTPServer((config.host, config.port), create_handler(state))


def main(argv: list[str] | None = None) -> None:
    """Run a participant service from a JSON config."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = load_party_config(args.config)
    server = create_server(config)
    LOGGER.info("party=%s listening on %s:%s", config.party_id, config.host, config.port)
    server.serve_forever()
