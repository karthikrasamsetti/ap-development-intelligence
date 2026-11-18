import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from app.identity_v9 import normalize, suggest, compare_cost

def test_identity_hindupur():
    assert suggest('GC- Hindupur',[{'candidate_id':18,'title':'MSE-CDP Hindupur1'}])[0]['candidate_id']==18

def test_identity_machilipatnam():
    assert suggest('JP- Machilipatnam',[{'candidate_id':20,'title':'MSE-CDP JP- Machilipatnam3'}])[0]['candidate_id']==20

def test_no_partial_place_matches():
    assert suggest('IP Gopavaram',[{'candidate_id':9,'title':'Gopavaram Extension'}])==[]

def test_cost_match_conflict_and_missing():
    records=[{'kind':'approved_project_cost','review_status':'approved','converted_amount_crore':'15.254900'}]
    assert compare_cost('1525.49',records)=='match'
    assert compare_cost('2140.00',records)=='conflict'
    assert compare_cost('1525.49',[])=='no_approved'
