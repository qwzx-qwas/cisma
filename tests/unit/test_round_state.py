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


# ── Initial state ────────────────────────────────────────────────────

def test_initial_state() -> None:
    """轮次初始状态正确"""
    r = AggregationRound("r1", ("P1", "P2", "P3"), 3)
    assert r.round_id == "r1"
    assert r.participant_ids == ("P1", "P2", "P3")
    assert r.vector_length == 3
    assert r.status == RoundStatus.CREATED
    assert r.received_shares == {}
    assert r.aggregate_shares == {}
    assert r.error_message is None


# ── Received share transitions ───────────────────────────────────────

def test_received_share_state_transitions() -> None:
    """轮次状态转换 — 符合状态机"""
    round_state = AggregationRound("r1", ("P1", "P2", "P3"), 2)

    round_state.add_received_share("P1", [1, 2])
    assert round_state.status == RoundStatus.COLLECTING_SHARES
    round_state.add_received_share("P2", [3, 4])
    round_state.add_received_share("P3", [5, 6])

    assert round_state.all_shares_received()
    assert round_state.status == RoundStatus.SHARES_READY


# ── Validation errors ────────────────────────────────────────────────

def test_duplicate_unknown_and_wrong_length_are_rejected() -> None:
    """重复提交 — 拒绝；未知参与方提交 — 拒绝"""
    round_state = AggregationRound("r1", ("P1", "P2", "P3"), 2)
    round_state.add_received_share("P1", [1, 2])

    with pytest.raises(DuplicateMessageError):
        round_state.add_received_share("P1", [1, 2])
    with pytest.raises(UnknownParticipantError):
        round_state.add_received_share("P4", [1, 2])
    with pytest.raises(DimensionMismatchError):
        round_state.add_received_share("P2", [1])


def test_wrong_vector_length_rejected() -> None:
    """错误向量长度 — 拒绝"""
    r = AggregationRound("r1", ("P1", "P2"), 5)
    with pytest.raises(DimensionMismatchError):
        r.add_received_share("P1", [1, 2])


# ── Aggregate shares ─────────────────────────────────────────────────

def test_aggregate_shares_can_complete_round() -> None:
    round_state = AggregationRound("r1", ("P1", "P2", "P3"), 0)

    round_state.add_aggregate_share("P1", [])
    round_state.add_aggregate_share("P2", [])
    round_state.add_aggregate_share("P3", [])
    round_state.complete()

    assert round_state.all_aggregate_shares_received()
    assert round_state.status == RoundStatus.COMPLETED


def test_duplicate_aggregate_share_rejected() -> None:
    """聚合份额重复提交 — 拒绝"""
    r = AggregationRound("r1", ("P1", "P2"), 2)
    r.add_aggregate_share("P1", [1, 2])
    with pytest.raises(DuplicateMessageError):
        r.add_aggregate_share("P1", [3, 4])


def test_unknown_participant_aggregate_rejected() -> None:
    """未知参与方聚合份额 — 拒绝"""
    r = AggregationRound("r1", ("P1", "P2"), 2)
    with pytest.raises(UnknownParticipantError):
        r.add_aggregate_share("P4", [1, 2])


def test_wrong_length_aggregate_rejected() -> None:
    """错误长度的聚合份额 — 拒绝"""
    r = AggregationRound("r1", ("P1", "P2"), 3)
    with pytest.raises(DimensionMismatchError):
        r.add_aggregate_share("P1", [1, 2])


# ── Complete / Fail state guards ─────────────────────────────────────

def test_completed_and_failed_rounds_reject_writes() -> None:
    """已完成轮次再次写入 — 拒绝"""
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


def test_fail_marks_round_with_message() -> None:
    r = AggregationRound("r1", ("P1", "P2"), 2)
    r.fail("timeout")
    assert r.status == RoundStatus.FAILED
    assert r.error_message == "timeout"


def test_failed_round_cannot_complete() -> None:
    r = AggregationRound("r1", ("P1", "P2"), 2)
    r.fail("error")
    with pytest.raises(InvalidRoundStateError):
        r.complete()


# ── Wrong round id ───────────────────────────────────────────────────

def test_wrong_round_id_is_rejected() -> None:
    """错误轮次提交 — 拒绝"""
    round_state = AggregationRound("r1", ("P1", "P2", "P3"), 1)
    with pytest.raises(InvalidRoundStateError):
        round_state.validate_round_id("r2")


# ── Multi-round isolation ────────────────────────────────────────────

def test_multiple_rounds_independent() -> None:
    """多个轮次状态独立"""
    r1 = AggregationRound("r1", ("P1",), 2)
    r2 = AggregationRound("r2", ("P1", "P2"), 3)

    r1.add_received_share("P1", [1, 2])
    assert "P1" in r1.received_shares
    assert r2.received_shares == {}

    r2.add_received_share("P1", [3, 4, 5])
    assert r1.received_shares["P1"] == [1, 2]
    assert r2.received_shares["P1"] == [3, 4, 5]


# ── Status enum ──────────────────────────────────────────────────────

def test_status_enum_values() -> None:
    assert RoundStatus.CREATED.value == "created"
    assert RoundStatus.COLLECTING_SHARES.value == "collecting_shares"
    assert RoundStatus.SHARES_READY.value == "shares_ready"
    assert RoundStatus.AGGREGATED.value == "aggregated"
    assert RoundStatus.COMPLETED.value == "completed"
    assert RoundStatus.FAILED.value == "failed"
