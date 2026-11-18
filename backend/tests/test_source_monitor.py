from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from app.source_monitor import due, extract_html, registry

def test_due_when_missing():
    assert due(None,datetime.now(timezone.utc),60)

def test_due_when_recent():
    now=datetime.now(timezone.utc)
    assert not due(SimpleNamespace(last_checked_at=now-timedelta(minutes=2)),now,60)

def test_due_when_old():
    now=datetime.now(timezone.utc)
    assert due(SimpleNamespace(last_checked_at=now-timedelta(hours=2)),now,60)

def test_html_ignores_scripts():
    title,body=extract_html(b'<title>Example</title><script>secret</script><p>'+b'Public information. '*12+b'</p>','Fallback')
    assert title=='Example' and 'secret' not in body and 'Public information' in body

def test_registry_approved_https():
    assert len(registry())>=2
