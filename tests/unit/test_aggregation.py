import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from secure_agg.constants import PARTY_COUNT
from secure_agg.core.aggregation import (
    aggregate_received_shares,
    plaintext_average,
    plaintext_sum,
    reconstruct_aggregation,
    AggregationResult,
)
from secure_agg.crypto.fixed_point import encode_vector
from secure_agg.crypto.secret_sharing import split_vector
from secure_agg.exceptions import DimensionMismatchError, InvalidShareError


def _secure_aggregate(parameter_vectors: list[list[float]]):
    per_sender_shares = [split_vector(encode_vector(values)) for values in parameter_vectors]
    aggregate_shares = []
    for party_index in range(PARTY_COUNT):
        received = [sender_shares[party_index] for sender_shares in per_sender_shares]
        aggregate_shares.append(aggregate_received_shares(received))
    return reconstruct_aggregation(aggregate_shares)


# ── Plaintext sum / average ──────────────────────────────────────────

def test_plaintext_sum_and_average() -> None:
    vectors = [[1.0, 2.0], [3.0, 4.0], [-1.0, 0.5]]

    assert plaintext_sum(vectors) == pytest.approx([3.0, 6.5])
    assert plaintext_average(vectors) == pytest.approx([1.0, 2.1666666667])


def test_plaintext_sum_three_parties_standard() -> None:
    """三组明文参数求和 — 结果正确"""
    p1, p2, p3 = [1.0, 2.0, 3.0], [2.0, 4.0, 6.0], [3.0, 6.0, 9.0]
    assert plaintext_sum([p1, p2, p3]) == [6.0, 12.0, 18.0]


def test_plaintext_average_three_parties_standard() -> None:
    """三组明文参数平均 — 结果正确"""
    p1, p2, p3 = [1.0, 2.0, 3.0], [2.0, 4.0, 6.0], [3.0, 6.0, 9.0]
    assert plaintext_average([p1, p2, p3]) == [2.0, 4.0, 6.0]


def test_plaintext_empty_list() -> None:
    """空数组 — 明确定义行为"""
    assert plaintext_sum([]) == []
    assert plaintext_average([]) == []


def test_plaintext_single_party() -> None:
    assert plaintext_sum([[10.0, 20.0]]) == [10.0, 20.0]
    assert plaintext_average([[10.0, 20.0]]) == [10.0, 20.0]


def test_plaintext_all_zeros() -> None:
    assert plaintext_sum([[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]) == [0.0, 0.0]
    assert plaintext_average([[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]) == [0.0, 0.0]


def test_plaintext_dimension_mismatch() -> None:
    """参数长度不同 — 抛出维度异常"""
    with pytest.raises(DimensionMismatchError):
        plaintext_sum([[1.0], [1.0, 2.0]])
    with pytest.raises(DimensionMismatchError):
        plaintext_average([[1.0], [1.0, 2.0]])


# ── Secure aggregation (full pipeline) ───────────────────────────────

def test_secure_aggregation_matches_plaintext_baseline() -> None:
    """三个聚合份额恢复 — 与明文基线一致"""
    vectors = [[1.0, 2.0, 3.0], [2.0, 4.0, 6.0], [3.0, 6.0, 9.0]]
    result = _secure_aggregate(vectors)

    assert result.sum_values == pytest.approx(plaintext_sum(vectors), abs=1e-5)
    assert result.average_values == pytest.approx(plaintext_average(vectors), abs=1e-5)
    assert result.participant_count == PARTY_COUNT


def test_secure_aggregation_handles_mixed_signs_and_decimals() -> None:
    """正负小数混合 — 正确处理"""
    vectors = [[-1.5, 2.25], [3.0, -4.5], [0.5, 1.25]]
    result = _secure_aggregate(vectors)
    assert result.sum_values == pytest.approx([2.0, -1.0], abs=1e-5)
    assert result.average_values == pytest.approx([0.666667, -0.333333], abs=1e-5)


def test_secure_aggregation_zeros() -> None:
    """全零参数 — 正确处理"""
    result = _secure_aggregate([[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]])
    assert result.sum_values == [0.0, 0.0]
    assert result.average_values == [0.0, 0.0]


def test_secure_aggregation_single_element() -> None:
    """单元素向量"""
    result = _secure_aggregate([[1.0], [2.0], [3.0]])
    assert result.sum_values == pytest.approx([6.0], abs=1e-5)


def test_secure_aggregation_accuracy_within_tolerance() -> None:
    """安全聚合结果与明文基线误差不超过 1e-5"""
    p1 = [1.234567, -2.345678, 3.456789]
    p2 = [4.567890, -5.678901, 6.789012]
    p3 = [7.890123, -8.901234, 9.012345]
    result = _secure_aggregate([p1, p2, p3])

    expected_sum = [p1[i] + p2[i] + p3[i] for i in range(3)]
    expected_avg = [v / 3 for v in expected_sum]

    for secure, expected in zip(result.sum_values, expected_sum):
        assert abs(secure - expected) <= 1e-5, f"sum {secure} != {expected}"
    for secure, expected in zip(result.average_values, expected_avg):
        assert abs(secure - expected) <= 1e-5, f"avg {secure} != {expected}"


# ── aggregate_received_shares ────────────────────────────────────────

def test_aggregate_received_shares_basic() -> None:
    """三组秘密份额本地聚合 — 结果维度正确"""
    result = aggregate_received_shares([[10, 20, 30], [5, 15, 25], [3, 7, 11]])
    assert result == [18, 42, 66]


def test_empty_vector_shares_are_supported() -> None:
    """空数组 — 明确定义行为"""
    assert aggregate_received_shares([[], [], []]) == []


def test_aggregate_shares_modular_arithmetic() -> None:
    """聚合结果在有限域范围内"""
    from secure_agg.constants import PRIME
    large = PRIME - 1
    result = aggregate_received_shares([[large], [10], [5]])
    assert 0 <= result[0] < PRIME
    assert result[0] == (large + 10 + 5) % PRIME


def test_dimension_mismatch_is_rejected() -> None:
    with pytest.raises(DimensionMismatchError):
        plaintext_sum([[1.0], [1.0, 2.0]])
    with pytest.raises(DimensionMismatchError):
        aggregate_received_shares([[1], [2, 3], [4]])


# ── reconstruct_aggregation ──────────────────────────────────────────

def test_reconstruct_aggregation_basic() -> None:
    result = reconstruct_aggregation([[1, 2], [3, 4], [5, 6]])
    assert result.sum_values == pytest.approx([9.0, 12.0], abs=1e-5)
    assert result.average_values == pytest.approx([3.0, 4.0], abs=1e-5)


def test_reconstruct_empty_vectors() -> None:
    result = reconstruct_aggregation([[], [], []])
    assert result.sum_values == []
    assert result.average_values == []


def test_incomplete_shares_are_rejected() -> None:
    with pytest.raises(InvalidShareError):
        aggregate_received_shares([[1], [2]])
    with pytest.raises(InvalidShareError):
        reconstruct_aggregation([[1], [2]])


def test_reconstruct_dimension_mismatch_raises() -> None:
    with pytest.raises(DimensionMismatchError):
        reconstruct_aggregation([[1, 2], [1, 2, 3]])


# ── AggregationResult dataclass ──────────────────────────────────────

def test_aggregation_result_dataclass() -> None:
    result = AggregationResult(
        encoded_sum=[6],
        sum_values=[6.0],
        average_values=[2.0],
        participant_count=3,
    )
    assert result.encoded_sum == [6]
    assert result.sum_values == [6.0]
    assert result.average_values == [2.0]
    assert result.participant_count == 3


# ── Large random test ────────────────────────────────────────────────

def test_secure_aggregation_random_vectors() -> None:
    """随机大向量测试 — 安全聚合与明文基线一致"""
    import random
    random.seed(42)
    p1 = [random.uniform(-10, 10) for _ in range(50)]
    p2 = [random.uniform(-10, 10) for _ in range(50)]
    p3 = [random.uniform(-10, 10) for _ in range(50)]

    result = _secure_aggregate([p1, p2, p3])
    expected_sum = plaintext_sum([p1, p2, p3])
    expected_avg = plaintext_average([p1, p2, p3])

    for s, e in zip(result.sum_values, expected_sum):
        assert abs(s - e) <= 1e-5
    for s, e in zip(result.average_values, expected_avg):
        assert abs(s - e) <= 1e-5
