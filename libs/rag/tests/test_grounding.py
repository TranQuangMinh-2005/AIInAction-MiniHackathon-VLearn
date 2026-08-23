from local_rag.grounding import apply_verification
from local_rag.models import SearchResult


def _source():
    return SearchResult(
        chunk_id="chunk",
        source="paper.pdf",
        title="Paper",
        page=1,
        content=(
            "Our machine learning model reduces expected losses by 15%. "
            "Optimization further reduces expected losses by 52%."
        ),
        score=0.9,
        dense_score=0.8,
        keyword_score=1.0,
        section="Abstract",
    )


def test_verification_uses_exact_span_and_unique_claim_label():
    answer = "The model reduces expected losses by 15% [S1]."
    verification = {
        "all_claims_supported": True,
        "items": [
            {
                "id": "C1",
                "entailed": True,
                "quote": (
                    "Our machine learning model reduces expected losses by 15%."
                ),
                "reason": "Directly stated.",
            }
        ],
    }

    relabeled, citations, grounded = apply_verification(
        answer, [_source()], verification
    )

    assert relabeled == answer
    assert citations[0].quote in _source().content
    assert citations[0].claim.startswith("The model")
    assert citations[0].entailed is True
    assert grounded is True


def test_grounded_is_false_when_quote_does_not_entail_claim():
    answer = "The model eliminates all fraud [S1]."
    verification = {
        "all_claims_supported": False,
        "items": [
            {
                "id": "C1",
                "entailed": False,
                "quote": "",
                "reason": "Not stated.",
            }
        ],
    }

    _, citations, grounded = apply_verification(
        answer, [_source()], verification
    )

    assert citations[0].entailed is False
    assert citations[0].quote in _source().content
    assert grounded is False


def test_repeated_source_labels_become_claim_level_labels():
    answer = "First claim [S1].\nSecond claim [S1]."
    verification = {
        "all_claims_supported": True,
        "items": [
            {
                "id": "C1",
                "entailed": True,
                "quote": "Our machine learning model reduces expected losses by 15%.",
                "reason": "Supported.",
            },
            {
                "id": "C2",
                "entailed": True,
                "quote": "Optimization further reduces expected losses by 52%.",
                "reason": "Supported.",
            },
        ],
    }

    relabeled, citations, grounded = apply_verification(
        answer, [_source()], verification
    )

    assert relabeled == "First claim [S1].\nSecond claim [S2]."
    assert [citation.label for citation in citations] == ["S1", "S2"]
    assert grounded is True


def test_grouped_source_labels_are_split_into_auditable_labels():
    answer = "The two findings are supported [S1, S2]."
    sources = [_source(), _source()]
    verification = {
        "all_claims_supported": True,
        "items": [
            {
                "id": "C1",
                "entailed": True,
                "quote": "Our machine learning model reduces expected losses by 15%.",
                "reason": "Supported.",
            },
            {
                "id": "C2",
                "entailed": True,
                "quote": "Optimization further reduces expected losses by 52%.",
                "reason": "Supported.",
            },
        ],
    }

    relabeled, citations, grounded = apply_verification(
        answer, sources, verification
    )

    assert relabeled == "The two findings are supported [S1] [S2]."
    assert len(citations) == 2
    assert grounded is True
