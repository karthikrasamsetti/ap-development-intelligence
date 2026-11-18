from types import SimpleNamespace
from app.discovery_relevance import assess, duplicate_hints

def test_project_status_ranks_above_contact_list():
    high = assess('MSE CDP Projects-Status', 'https://apiic.in/docs/MSE-CDP-Projects-Status.pdf')
    low = assess('IALA Commissioners/EOs Contact Details', 'https://apiic.in/contacts.pdf')
    assert high['score'] > low['score']
    assert high['priority'] == 'high'
    assert low['priority'] == 'low'

def test_administrative_policy_low():
    assert assess('Sexual Harassment Policy','https://apiic.in/policy.pdf')['priority'] == 'low'

def test_not_automatic_approval():
    assert assess('Industrial Parks','https://apiic.in/industrial-parks/')['review_required'] is True

def test_duplicate_hints_are_source_scoped():
    rows = [
        SimpleNamespace(id=1,title='Industrial Parks Development Projects',parent_source_key='a'),
        SimpleNamespace(id=2,title='Industrial Parks Development Projects',parent_source_key='a'),
        SimpleNamespace(id=3,title='Industrial Parks Development Projects',parent_source_key='b'),
    ]
    hints=duplicate_hints(rows)
    assert hints[1]==[2]
    assert hints[3]==[]

def test_query_not_used_to_score():
    assert assess('About','https://apiic.in/about?project-status=1')['score'] == assess('About','https://apiic.in/about')['score']
