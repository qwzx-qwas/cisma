import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from secure_agg.core.round_state import AggregationRound, RoundStatus
from secure_agg.exceptions import (
    DimensionMismatchError,
    DuplicateMessageError,
    InvalidRoundStateError,
    UnknownParticipantError,
)


def test_received_share_state_transitions() -> None:
    round_state = AggregationRound("r1", ("P1", "P2", "P3"), 2)

    round_state.add_received_share("P1", [1, 2])
    assert round_state.status == RoundStatus.COLLECTING_SHARES
    round_state.add_received_share("P2", [3, 4])
    round_state.add_received_share("P3", [5, 6])

    assert round_state.all_shares_received()
    assert round_state.status == RoundStatus.SHARES_READY


def test_duplicate_unknown_and_wrong_length_are_rejected() -> None:
    round_state = AggregationRound("r1", ("P1", "P2", "P3"), 2)
    round_state.add_received_share("P1", [1, 2])

    with pytest.raises(DuplicateMessageError):
        round_state.add_received_share("P1", [1, 2])
    with pytest.raises(UnknownParticipantError):
        round_state.add_received_share("P4", [1, 2])
    with pytest.raises(DimensionMismatchError):
        round_state.add_received_share("P2", [1])


def test_aggregate_shares_can_complete_round() -> None:
    round_state = AggregationRound("r1", ("P1", "P2", "P3"), 0)

    round_state.add_aggregate_share("P1", [])
    round_state.add_aggregate_share("P2", [])
    round_state.add_aggregate_share("P3", [])
    round_state.complete()

    assert round_state.all_aggregate_shares_received()
    assert round_state.status == RoundStatus.COMPLETED


def test_completed_and_failed_rounds_reject_writes() -> None:
    completed = AggregationRound("r1", ("P1", "P2", "P3"), 0)
    completed.add_aggregate_share("P1", [])
    completed.add_aggregate_share("P2", [])
    completed.add_aggregate_share("P3", [])
    completed.complete()

    with pytest.raises(InvalidRoundStateError):
        completed.add_aggregate_share("P1", [])

    failed = AggregationRound("r2", ("P1", "P2", "P3"), 0)
    failed.fail("bad digest")
    with pytest.raises(InvalidRoundStateError):
        failed.add_received_share("P1", [])


def test_wrong_round_id_is_rejected() -> None:
    round_state = AggregationRound("r1", ("P1", "P2", "P3"), 1)

    with pytest.raises(InvalidRoundStateError):
        round_state.validate_round_id("r2")
