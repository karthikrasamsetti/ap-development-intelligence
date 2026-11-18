"""Allowlisted source monitoring; run via external scheduler or admin endpoint.
No extraction, AI calls, or publication occurs here.
"""
import hashlib
import ipaddress
import json
import re
import socket
import urllib.request
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from urllib.parse import urlparse
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from .models import IngestionSnapshot, SourceMonitorRun, SourceMonitorState
from .source_registry import SOURCES

MAX_BYTES = 1_500_000
MAX_TEXT = 40_000

def utcnow(): return datetime.now(timezone.utc)

def registry():
    keys = [s['key'] for s in SOURCES]
    if len(keys) != len(set(keys)): raise ValueError('Duplicate source keys in registry')
    for s in SOURCES:
        p = urlparse(s['url'])
        if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None,443):
            raise ValueError('Invalid registry URL')
    return SOURCES

class HTMLText(HTMLParser):
    def __init__(self):
        super().__init__(); self.skip=0; self.title_depth=0; self.title=[]; self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','noscript'): self.skip+=1
        if tag=='title': self.title_depth+=1
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript'): self.skip=max(0,self.skip-1)
        if tag=='title': self.title_depth=max(0,self.title_depth-1)
    def handle_data(self,data):
        if self.title_depth: self.title.append(data)
        if not self.skip: self.parts.append(data)

def extract_html(raw, fallback):
    parser=HTMLText(); parser.feed(raw.decode('utf-8',errors='replace'))
    content=re.sub(r'\s+',' ',' '.join(parser.parts)).strip()[:MAX_TEXT]
    title=re.sub(r'\s+',' ',' '.join(parser.title)).strip()[:300] or fallback
    if len(content)<100: raise ValueError('Insufficient HTML text')
    return title,content

def check_host(host):
    # Fail closed if DNS yields any private, loopback, reserved or non-global address.
    addresses=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
    if not addresses: raise ValueError('Unresolvable host')
    for a in addresses:
        if not ipaddress.ip_address(a[4][0]).is_global: raise ValueError('Source host resolves to a non-public address')

def fetch_html(src):
    url=src['url']; p=urlparse(url)
    if p.scheme!='https' or not p.hostname: raise ValueError('HTTPS required')
    check_host(p.hostname)
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise ValueError('Redirect refused: update approved source URL manually')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect)
    request=urllib.request.Request(url,headers={'User-Agent':'APDIResearchBot/0.2 (public evidence monitoring)','Accept':'text/html'})
    with opener.open(request,timeout=20) as response:
        if 'text/html' not in response.headers.get('Content-Type','').lower(): raise ValueError('Expected HTML response')
        raw=response.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES: raise ValueError('HTML response exceeds size limit')
    return extract_html(raw,src['name'])

def due(state,now,interval_minutes):
    if state is None or state.last_checked_at is None: return True
    last=state.last_checked_at
    if last.tzinfo is None: last=last.replace(tzinfo=timezone.utc)
    return now-last>=timedelta(minutes=interval_minutes)

def record_one(db:Session, src, *, force=False, fetcher=fetch_html, now=None):
    now=now or utcnow(); key=src['key']; interval=max(15,int(src.get('interval_minutes',1440)))
    state=db.get(SourceMonitorState,key)
    if state is None:
        state=SourceMonitorState(source_key=key,source_url=src['url'],enabled=True,consecutive_failures=0)
        db.add(state); db.flush()
    if not state.enabled: return {'source_key':key,'result':'disabled'}
    if not force and not due(state,now,interval): return {'source_key':key,'result':'not_due'}
    run=SourceMonitorRun(source_key=key,started_at=now,result='running')
    db.add(run); db.flush()
    try:
        title,content=fetcher(src)
        digest=hashlib.sha256(content.encode('utf-8')).hexdigest()
        prior=db.scalar(select(IngestionSnapshot).where(IngestionSnapshot.source_key==key,IngestionSnapshot.content_hash==digest))
        if prior:
            result='unchanged'; snapshot_id=prior.id
        else:
            snap=IngestionSnapshot(source_key=key,source_name=src['name'],url=src['url'],title=title,content_hash=digest,excerpt=content[:1500],body_text=content,review_status='pending',fetched_at=now)
            db.add(snap); db.flush(); snapshot_id=snap.id; result='new_snapshot'
        state.last_success_at=now; state.last_snapshot_id=snapshot_id; state.last_content_hash=digest; state.consecutive_failures=0; state.last_error=None
        run.snapshot_id=snapshot_id; run.result=result
    except Exception as exc:
        result='error'; state.consecutive_failures+=1
        # Avoid storing secrets or unbounded server messages.
        state.last_error=f'{type(exc).__name__}: {str(exc)[:250]}'
        run.result=result; run.error_message=state.last_error
    state.source_url=src['url']; state.last_checked_at=now; run.finished_at=utcnow()
    db.commit()
    return {'source_key':key,'result':result,'snapshot_id':run.snapshot_id,'error':run.error_message}

def run_monitor(db:Session, *, keys=None, force=False, fetcher=fetch_html):
    sources=registry()
    if keys:
        unknown=set(keys)-{s['key'] for s in sources}
        if unknown: raise ValueError('Unknown source keys: '+', '.join(sorted(unknown)))
        sources=[s for s in sources if s['key'] in keys]
    # Session-level advisory lock, non-blocking, prevents overlapping scheduler/API runs.
    locked=bool(db.scalar(text('SELECT pg_try_advisory_lock(738291104)')))
    if not locked: return {'result':'already_running','sources':[]}
    try:
        output=[record_one(db,s,force=force,fetcher=fetcher) for s in sources]
        return {'result':'complete','sources':output}
    finally:
        db.execute(text('SELECT pg_advisory_unlock(738291104)')); db.commit()
