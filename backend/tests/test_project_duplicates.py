from types import SimpleNamespace
from app.project_duplicates import normalize_title, cross_snapshot_suggestions


def test_name_normalization():
    assert normalize_title('MSE CDP IP-Guttapadu') == normalize_title('Industrial Park Guttapadu')


def test_cross_snapshot_only():
    first = SimpleNamespace(id=1, snapshot_id=4, title='MSE CDP IP-Guttapadu', review_status='draft')
    same = SimpleNamespace(id=2, snapshot_id=4, title='Industrial Park Guttapadu', review_status='draft')
    other = SimpleNamespace(id=3, snapshot_id=5, title='Industrial Park Guttapadu', review_status='published')
    result = cross_snapshot_suggestions(first, [first, same, other])
    assert [item['id'] for item in result] == [3]
