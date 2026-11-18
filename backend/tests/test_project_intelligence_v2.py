from app.project_intelligence_v2 import inspect_tables, identity_suggestions, evidence_timeline, build_report

def test_header_is_not_project():
    p=[{'page':1,'text':'S.No IP Name Letter No (Component Wise)\nRs in Lakhs\n1 IP-Gopavaram details\nRoads 1.00 2.00 3.00'}]
    r=inspect_tables(p)
    assert r['project_mentions']==1
    assert r['projects'][0]['project_hint']=='IP-Gopavaram'

def test_neighboring_projects_cannot_share_total():
    p=[{'page':5,'text':'Rs in Lakhs\n8 IP-Gopavaram details\nRoads 1.00 2.00 3.00\n9 IP-Guttapadu details\nTotal:\n1050.00 1090.00 2140.00 1020.10\n10 IP-Jagadurthy details'}]
    r=inspect_tables(p)
    assert r['project_mentions']==3
    a,b,c=r['projects']
    assert not a['total_candidates'] and not c['total_candidates']
    assert b['total_candidates'][0]['tokens'][2]=='2140.00'
    assert b['total_candidates'][0]['financial_kind']=='unassigned'
    assert r['verified_financial_assignments']==0

def test_unnumbered_anchor_does_not_claim_next_project_total():
    p=[{'page':1,'text':'Rs in Lakhs\nIP-Gopavaram details\n9 IP-Guttapadu details\nTotal:\n1050.00 1090.00 2140.00'}]
    r=inspect_tables(p)
    assert not r['projects'][0]['total_candidates']

def test_component_is_not_project():
    p=[{'page':1,'text':'Rs in Lakhs\nMSE-CDP IP- Water Harvesting 7.00 3.00 10.00\n9 IP-Guttapadu details'}]
    assert inspect_tables(p)['project_mentions']==1

def test_identity_suggestions_do_not_merge():
    c=[{'id':1,'title':'IP-Guttapadu'},{'id':2,'title':'IP Guttapadu'},{'id':3,'title':'IP-Gopavaram'}]
    r=identity_suggestions(c)
    assert len(r)==1 and len(r[0]['members'])==2
    assert r[0]['action']=='review_only_no_auto_merge'

def test_timeline_is_source_observation():
    r=evidence_timeline([{'candidate_id':29,'source_date':'2025-01-01','observed_status':'grounded','quote':'Roads work in progress','snapshot_id':4},{'source_date':'bad'}])
    assert len(r)==1 and r[0]['classification']=='source_observation_not_verified_milestone'

def test_conflict_integrated_without_mutation():
    c=[{'id':29,'title':'IP-Guttapadu','investment_inr_crore':'13.79'}]
    f=[{'id':1,'candidate_id':29,'kind':'approved_project_cost','review_status':'approved','converted_amount_crore':'21.40'}]
    r=build_report(candidates=c,financial_evidence=f)
    assert r['financial_conflicts'][0]['status']=='draft_differs_from_approved_cost'
    assert c[0]['investment_inr_crore']=='13.79'
