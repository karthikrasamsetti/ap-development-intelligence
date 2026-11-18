from app.public_intelligence_api import public_draft_previews_enabled

def test_drafts_withheld_by_default(monkeypatch):
    monkeypatch.delenv('APDI_PUBLIC_DRAFT_PREVIEWS', raising=False)
    assert public_draft_previews_enabled() is False

def test_drafts_withheld_for_invalid_values(monkeypatch):
    monkeypatch.setenv('APDI_PUBLIC_DRAFT_PREVIEWS', 'false')
    assert public_draft_previews_enabled() is False

def test_demo_opt_in_explicit(monkeypatch):
    monkeypatch.setenv('APDI_PUBLIC_DRAFT_PREVIEWS', 'true')
    assert public_draft_previews_enabled() is True
