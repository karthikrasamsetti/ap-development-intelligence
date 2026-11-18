from app.discovery import normalize_link,allowed,suggest_links

def test_relative_link():
    assert normalize_link('/investment/project','https://apiic.in/')=='https://apiic.in/investment/project'
def test_cross_domain_rejected():
    assert normalize_link('https://evil.example/investment','https://apiic.in/') is None
def test_http_rejected():
    assert normalize_link('http://apiic.in/investment','https://apiic.in/') is None
def test_query_removed():
    assert normalize_link('/investment?tracking=1','https://apiic.in/')=='https://apiic.in/investment'
def test_credentials_rejected():
    assert not allowed('https://x@apiic.in/','https://apiic.in/')
def test_discovery_keyword_filter():
    result=suggest_links('https://apiic.in/','<a href="/investment">Investment</a><a href="/about">About</a>')
    assert list(result)==['https://apiic.in/investment']
def test_pdf():
    assert normalize_link('/docs/project.pdf','https://apiic.in/')=='https://apiic.in/docs/project.pdf'
