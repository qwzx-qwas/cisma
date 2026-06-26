"""Aggregation round state machine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from secure_agg.exceptions import (
    DimensionMismatchError,
    DuplicateMessageError,
    InvalidRoundStateError,
    UnknownParticipantError,
)


class RoundStatus(str, Enum):
    """Lifecycle states for one aggregation round."""

    CREATED = "created"
    COLLECTING_SHARES = "collecting_shares"
    SHARES_READY = "shares_ready"
    AGGREGATED = "aggregated"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AggregationRound:
    """Mutable state for one local or coordinator aggregation round."""

    round_id: str
    participant_ids: tuple[str, ...]
    vector_length: int
    status: RoundStatus = RoundStatus.CREATED
    received_shares: dict[str, list[int]] = field(default_factory=dict)
    aggregate_shares: dict[str, list[int]] = field(default_factory=dict)
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate static round metadata."""
        if not self.round_id:
            raise ValueError("round_id must be non-empty")
        if not self.participant_ids:
            raise ValueError("participant_ids must be non-empty")
        if len(set(self.participant_ids)) != len(self.participant_ids):
            raise ValueError("participant_ids must be unique")
        if self.vector_length < 0:
            raise ValueError("vector_length must be non-negative")

    def validate_round_id(self, round_id: str) -> None:
        """Reject messages for a different round."""
        if round_id != self.round_id:
            raise InvalidRoundStateError("message round_id does not match this round")

    def _ensure_known_participant(self, participant_id: str) -> None:
        if participant_id not in self.participant_ids:
            raise UnknownParticipantError(f"unknown participant: {participant_id}")

    def _ensure_active(self) -> None:
        if self.status == RoundStatus.FAILED:
            raise InvalidRoundStateError("failed round cannot accept more data")
        if self.status == RoundStatus.COMPLETED:
            raise InvalidRoundStateError("completed round cannot accept more data")

    def _validate_share_length(self, share: list[int]) -> None:
        if len(share) != self.vector_length:
            raise DimensionMismatchError("share length does not match round vector length")

    def add_received_share(
        self,
        sender_id: str,
        share: list[int],
    ) -> None:
        """Record one received secret share for this round."""
        self._ensure_active()
        self._ensure_known_participant(sender_id)
        if sender_id in self.received_shares:
            raise DuplicateMessageError("received share already submitted")
        if self.status not in (RoundStatus.CREATED, RoundStatus.COLLECTING_SHARES):
            raise InvalidRoundStateError("round is not accepting received shares")
        self._validate_share_length(share)

        self.received_shares[sender_id] = list(share)
        self.status = (
            RoundStatus.SHARES_READY
            if self.all_shares_received()
            else RoundStatus.COLLECTING_SHARES
        )

    def all_shares_received(self) -> bool:
        """Return whether all participants have submitted local shares."""
        return set(self.received_shares) == set(self.participant_ids)

    def add_aggregate_share(
        self,
        party_id: str,
        share: list[int],
    ) -> None:
        """Record one aggregate share submitted to the coordinator."""
        self._ensure_active()
        self._ensure_known_participant(party_id)
        if party_id in self.aggregate_shares:
            raise DuplicateMessageError("aggregate share already submitted")
        if self.status not in (
            RoundStatus.CREATED,
            RoundStatus.COLLECTING_SHARES,
            RoundStatus.SHARES_READY,
            RoundStatus.AGGREGATED,
        ):
            raise InvalidRoundStateError("round is not accepting aggregate shares")
        self._validate_share_length(share)

        self.aggregate_shares[party_id] = list(share)
        self.status = RoundStatus.AGGREGATED

    def all_aggregate_shares_received(self) -> bool:
        """Return whether all participants have submitted aggregate shares."""
        return set(self.aggregate_shares) == set(self.participant_ids)

    def complete(self) -> None:
        """Mark the round as completed after successful reconstruction."""
        self._ensure_active()
        if not self.all_aggregate_shares_received():
            raise InvalidRoundStateError("cannot complete before all aggregate shares arrive")
        self.status = RoundStatus.COMPLETED

    def fail(self, message: str) -> None:
        """Move the round to a failed state with an explanatory message."""
        self.status = RoundStatus.FAILED
        self.error_message = message
