from app.project_intelligence_batch import scan_pages, conflicts, project_key

def test_page_finds_anchor_and_following_total():
    pages=[{'page':5,'text':'Rs. in Lakhs\nTotal\n100 200 300\nRoads 566.35 587.96 1154.31\n9 IP-Guttapadu DOC\nTotal\n1050.00 1090.00 2140.00 1020.10'}]
    r=scan_pages(pages)
    assert r['project_mentions']==1
    x=r['projects'][0]
    assert x['project_line']==5 and x['following_total_line']==6
    assert x['total_candidates'][0]['tokens'][2]=='2140.00'
    assert x['review_state']=='needs_visual_row_column_verification'

def test_ambiguous_anchor_flag():
    p=[{'page':1,'text':'Rs in Lakhs\nIP-Guttapadu\nIP-Tanuku\nTotal\n100 200'}]
    assert 'multiple_project_anchors_in_block' in scan_pages(p)['projects'][0]['flags']

def test_conflict_report_and_no_auto_update():
    c=[{'id':29,'title':'Guttapadu','investment_inr_crore':'13.79'}]
    f=[{'id':1,'candidate_id':29,'kind':'approved_project_cost','review_status':'approved','converted_amount_crore':'21.40'}]
    r=conflicts(c,f)
    assert r[0]['status']=='draft_differs_from_approved_cost'
    assert r[0]['action']=='manual_review_only'
    assert c[0]['investment_inr_crore']=='13.79'

def test_pending_ignored():
    assert conflicts([{'id':1}], [{'candidate_id':1,'kind':'approved_project_cost','review_status':'proposed'}])==[]

def test_grouping_is_advisory():
    assert project_key('IP-Guttapadu')==project_key('IP Guttapadu')
