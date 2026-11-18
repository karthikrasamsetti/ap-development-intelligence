from app.pdf_table_review import inspect_pages

def test_keeps_page_and_line_context():
    result = inspect_pages([
        {'page': 1, 'text': 'MSE CDP IP-Guttapadu\nTotal (Rs. in Lakhs)\nTotal 1001.00 429.00 1430.00'},
        {'page': 2, 'text': 'MSE CDP IP-Tanuku\nTotal 753.49 322.92 1076.41'}])
    assert result['pages_inspected'] == 2
    assert result['pages_with_hits'][0]['hits'][0]['project_name_hints'] == ['MSE CDP IP-Guttapadu']
    assert result['pages_with_hits'][1]['page'] == 2
    assert result['pages_with_hits'][0]['hits'][2]['numeric_tokens'] == ['1001.00', '429.00', '1430.00']

def test_does_not_assert_amount_attribution():
    result = inspect_pages([{'page': 1, 'text': 'MSE CDP IP-Guttapadu\nTotal 1379.45 1375.87'}])
    assert 'investment_inr_crore' not in str(result)
    assert 'Do not attribute' in result['caution']

def test_handles_no_text():
    result = inspect_pages([{'page': 1, 'text': ''}])
    assert result['pages_with_hits'] == []
