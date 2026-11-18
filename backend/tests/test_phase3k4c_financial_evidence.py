from decimal import Decimal
import pytest
from app.financial_evidence import validate_proposal

BASE = dict(state='proposed_unpublished', project='MSE CDP IP-Guttapadu', kind='approved_project_cost',
 source_page=5, source_line=22, source_amount_index=2, source_amount_token='2140.00',
 source_text='1050.00 1090.00 2140.00 1020.10', original_amount_lakh='2140.00',
 converted_amount_crore='21.40', project_anchor={'page':5,'line':19,'text':'9 IP-Guttapadu'},
 unit_evidence={'page':5,'line':5,'text':'Rs. in Lakhs'}, reviewer_verified_row_and_column=True)

def test_valid(): assert validate_proposal(BASE) == Decimal('2140.00')
@pytest.mark.parametrize('change', [
 {'converted_amount_crore':'13.79'}, {'original_amount_lakh':'1379.45'},
 {'reviewer_verified_row_and_column':False}, {'source_page':0},
 {'kind':'investment'}, {'unit_evidence':{'page':5,'line':5,'text':'Rs. in Crores'}},
 {'source_amount_token':'9999.00'}, {'project_anchor':{'page':5,'line':19,'text':'Other project'}},
])
def test_invalid(change):
    with pytest.raises(ValueError): validate_proposal({**BASE, **change})
