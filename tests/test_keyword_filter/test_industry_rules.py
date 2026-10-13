from src.modules.keyword_filter.industry_rules import classify_keyword


def test_excludes_automotive_lighting_keywords():
    decision = classify_keyword("smoked headlights")
    assert not decision.keep
    assert decision.reason == "automotive lighting"


def test_excludes_local_retail_intent():
    decision = classify_keyword("led light store near me")
    assert not decision.keep
    assert decision.reason == "retail or local purchase intent"


def test_preserves_ambiguous_b2b_candidate_for_ai_review():
    decision = classify_keyword("lamp parts suppliers")
    assert decision.keep
    assert decision.reason is None
