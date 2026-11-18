from types import SimpleNamespace
from app.daily_intelligence import run_daily

class DB:
    def __init__(self, locked=True): self.locked=locked; self.commits=0; self.rollbacks=0
    def scalar(self, query, params=None): return self.locked
    def execute(self, query, params=None): pass
    def commit(self): self.commits+=1
    def rollback(self): self.rollbacks+=1

def test_daily_success():
    db=DB()
    def monitor(db, **kw): return {'result':'complete','sources':[{'source_key':'apiic-home','result':'new_snapshot'}]}
    def scan(db, key): return {'found':4,'new_proposals':2}
    result=run_daily(db, keys=['apiic-home'], monitor_runner=monitor, scanner=scan)
    assert result['summary']=={'sources_checked':1,'new_snapshots':1,'new_link_proposals':2,'errors':0}
    assert db.commits==1

def test_daily_scan_failure_does_not_publish_or_crash():
    db=DB()
    def monitor(db, **kw): return {'result':'complete','sources':[]}
    def scan(db, key): raise RuntimeError('network error')
    result=run_daily(db,keys=['apiic-home'],monitor_runner=monitor,scanner=scan)
    assert result['summary']['errors']==1 and result['discovery'][0]['error_type']=='RuntimeError'
    assert db.rollbacks==1

def test_daily_invalid_source_fails_closed():
    try: run_daily(DB(),keys=['untrusted-url'])
    except ValueError as e: assert 'Unknown source keys' in str(e)
    else: assert False

def test_daily_overlapping_run():
    result=run_daily(DB(locked=False),keys=['apiic-home'])
    assert result['result']=='already_running'

def test_daily_no_scan():
    def monitor(db,**kw): return {'result':'complete','sources':[]}
    result=run_daily(DB(),keys=['apiic-home'],scan_links=False,monitor_runner=monitor)
    assert result['discovery']==[]
