"""Quality guard: fail if a change makes the skill finder or the ranking WORSE.

Example: adding the alias "ai" for "machine learning" would create false alarms,
precision would drop below 0.95, and this test would catch it.
"""

import pytest

import evaluate


def test_skill_finder_quality_does_not_drop():
    report = evaluate.evaluate_skills(evaluate.load_cases()["jobs"])
    assert report["precision"] >= 0.95  # almost no false alarms
    assert report["f1"] >= 0.90


def test_obvious_ranking_pairs_are_all_correct():
    cases = evaluate.load_cases()
    result = evaluate.evaluate_ranking(cases["jobs"], cases["ranking_pairs"])
    assert result["correct"] == len(cases["ranking_pairs"])


def test_f1_math():
    # approx: computers store decimals slightly off (0.8 -> 0.8000000000000002)
    assert evaluate.f1(tp=8, fp=2, fn=2) == pytest.approx((0.8, 0.8, 0.8))
    assert evaluate.f1(tp=0, fp=0, fn=0) == (1.0, 1.0, 1.0)  # nothing to find, nothing found
