def test_scoring_engine_overdue_penalty():
    from src.linter.scoring_engine import compute_overall_score

    assert compute_overall_score(0) == 100
    assert compute_overall_score(3) == 97


def test_scoring_engine_clamps():
    from src.linter.scoring_engine import compute_overall_score

    assert compute_overall_score(150) == 0
