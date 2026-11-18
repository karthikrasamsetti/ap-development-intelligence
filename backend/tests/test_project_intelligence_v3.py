from app.project_intelligence_v3 import group_fragments, project_anchor, report_geometry


def test_header_and_component_excluded():
    assert project_anchor('S.No IP Name Letter No') is None
    assert project_anchor('2 MSE-CDP IP- Water Harvesting 7.00') is None
    assert project_anchor('9 IP-Guttapadu 23, Dt:06.11.2023') is not None


def test_geometry_line_order():
    lines = group_fragments([{'x': 40, 'y': 80, 'text': '2140.00'}, {'x': 10, 'y': 80, 'text': 'Total:'}, {'x': 10, 'y': 100, 'text': '9 IP-Guttapadu'}])
    assert lines[0]['text'] == '9 IP-Guttapadu'
    assert lines[1]['text'] == 'Total: 2140.00'


def test_total_not_stolen_by_next_project():
    def line(y, text):
        return {'y': y, 'text': text, 'fragments': [{'x': 10, 'y': y, 'text': text}]}
    pages = [{'page': 5, 'lines': [line(100, '8 IP Gopavaram'), line(90, 'Total: 100.00'), line(80, '9 IP-Guttapadu'), line(70, 'Total: 1050.00 1090.00 2140.00 1020.10'), line(60, '10 IP-Jagadurthy')]}]
    result = report_geometry(pages)
    assert len(result['projects']) == 3
    assert len(result['projects'][0]['total_candidates']) == 1
    assert result['projects'][1]['total_candidates'][0]['numeric_cells'][2]['text'] == '2140.00'
    assert result['verified_financial_assignments'] == 0


def test_multiple_totals_warns_and_never_assigns():
    def line(y, text):
        return {'y': y, 'text': text, 'fragments': [{'x': 10, 'y': y, 'text': text}]}
    pages = [{'page': 7, 'lines': [line(100, '14 IP Pagali'), line(90, 'Total: 1030.00'), line(80, 'Total: 2686.00')]}]
    project = report_geometry(pages)['projects'][0]
    assert 'multiple_totals_require_row_review' in project['flags']
    assert all(not row['column_verified'] for row in project['total_candidates'])
