from app.extraction_quality import good_project_name, supported_investment, supported_jobs

def test_project_titles():
    assert good_project_name('MSE CDP IP-Guttapadu')
    assert good_project_name('Donakonda Mega Industrial Hub')
    assert not good_project_name('With an investment of nearly ₹69,000 crore and the potential to generate 13,000 direct employment opportunities')
    assert not good_project_name('Parameter Details Investment ₹297 crore Expected Annual Turnover 1,950 jobs')
    assert not good_project_name('MSE-CDP Hindupur1')

def test_investment_requires_matching_amount_and_quote():
    source = 'Investment 13.79 crore at Guttapadu'
    assert supported_investment(13.79, source, source)
    assert not supported_investment(13.7, source, source)
    assert not supported_investment(13.79, 'Investment 13.79 crore', 'unrelated text')
    assert supported_investment(100000, '1 lakh crore', '1 lakh crore')

def test_jobs_require_context():
    assert supported_jobs(1950, '1,950 projected jobs', '1,950 projected jobs')
    assert not supported_jobs(1950, '1,950 projected jobs', '1,950 projected jobs', realized=True)
    assert supported_jobs(1950, '1,950 jobs created', '1,950 jobs created', realized=True)
