from types import SimpleNamespace
from app.pdf_review_v5_api import suggest_matches, MAX_PDF_BYTES

def test_matching_is_advisory_and_scoped():
    rows = [SimpleNamespace(id=29, title="MSE CDP IP-Guttapadu", review_status="draft"),
            SimpleNamespace(id=30, title="MSE CDP IP Gopavaram", review_status="draft")]
    matches = suggest_matches({"name":"IP-Guttapadu"}, rows)
    assert [m["candidate_id"] for m in matches] == [29]
    assert matches[0]["match_status"] == "possible_only"

def test_generic_project_tokens_cannot_match():
    assert suggest_matches({"name":"MSE CDP IP"}, [SimpleNamespace(id=1, title="MSE CDP IP", review_status="draft")]) == []

def test_upload_cap():
    assert MAX_PDF_BYTES == 15 * 1024 * 1024
