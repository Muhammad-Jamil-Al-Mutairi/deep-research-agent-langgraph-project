"""LoopDetector (given) and MetricStagnationDetector (HERMES extension)."""

from hermes.tools.verification.loop_detector import (
    LoopDetector,
    MetricStagnationDetector,
)


def test_exact_repetition_flagged_on_third_identical_call():
    d = LoopDetector()
    assert not d.check_tool_call("search_components", '{"category": "motor"}').is_looping
    assert not d.check_tool_call("search_components", '{"category": "motor"}').is_looping
    third = d.check_tool_call("search_components", '{"category": "motor"}')
    assert third.is_looping and third.strategy == "exact"


def test_fuzzy_repetition_flagged():
    d = LoopDetector()
    d.check_tool_call("search_web", "12V gear motor 30:1 encoder price")
    d.check_tool_call("search_web", "12V gear motor 30:1 encoder price list")
    result = d.check_tool_call("search_web", "12V gear motor 30:1 encoder price")
    assert result.is_looping


def test_different_calls_are_not_loops():
    d = LoopDetector()
    for q in ("battery 6000 mAh", "motor driver 12 A", "wheel 90 mm", "caster ball bearing"):
        assert not d.check_tool_call("search_components", q).is_looping


def test_text_stagnation():
    d = LoopDetector()
    for _ in range(2):
        assert not d.check_output_stagnation("swap battery for a larger LiPo pack").is_looping
    assert d.check_output_stagnation("swap battery for a larger LiPo pack").is_looping


def test_metric_stagnation_runtime_example():
    # Spec example: runtime 1.20 h, 1.21 h, 1.20 h against a 2.0 h requirement -> normalised shortfalls
    scores = [-(2.0 - r) / 2.0 for r in (1.20, 1.21, 1.20)]
    result = MetricStagnationDetector(window=3, epsilon=0.02).check(scores)
    assert result.is_looping and result.strategy == "stagnation"


def test_metric_progress_is_not_stagnation():
    assert not MetricStagnationDetector().check([-1.2, -0.6, -0.1]).is_looping
    assert not MetricStagnationDetector().check([-0.5, -0.5, 0.0]).is_looping  # a pass is progress
    assert not MetricStagnationDetector().check([-0.5, -0.5]).is_looping  # window not full
