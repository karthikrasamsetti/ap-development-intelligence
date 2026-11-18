"""Constrained same-host discovery; proposed URLs never become trusted automatically."""
import hashlib
import ipaddress
import re
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urldefrag
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import DiscoveryProposal, DiscoveryEvent, IngestionSnapshot
from .source_monitor import registry, check_host, extract_html

MAX_BYTES=1_500_000
KEYWORDS=('investment','industrial','project','development','port','infrastructure','notification','tender','mou','policy','scheme','press','release','announcement','pdf')

def utcnow(): return datetime.now(timezone.utc)
def allowed(url, base):
    p=urlparse(url); b=urlparse(base)
    return (p.scheme=='https' and p.hostname==b.hostname and p.port in (None,443)
            and not p.username and not p.password and not p.fragment and len(url)<=1500
            and p.path.lower().split('.')[-1] not in ('zip','exe','jpg','png','mp4','doc','docx'))

def normalize_link(href,base):
    if not href or href.startswith(('#','mailto:','javascript:','tel:')): return None
    url=urldefrag(urljoin(base,href))[0]
    p=urlparse(url)
    url=p._replace(query='').geturl()  # tracking and untrusted query strings excluded
    return url if allowed(url,base) else None

class Links(HTMLParser):
    def __init__(self): super().__init__(); self.links=[]; self.anchor=None; self.words=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a': self.anchor=dict(attrs).get('href'); self.words=[]
    def handle_data(self,data):
        if self.anchor is not None: self.words.append(data)
    def handle_endtag(self,tag):
        if tag=='a' and self.anchor is not None:
            self.links.append((self.anchor,' '.join(self.words).strip()[:300])); self.anchor=None

def fetch_bytes(url, accept='text/html,application/pdf'):
    p=urlparse(url)
    if p.scheme!='https' or not p.hostname: raise ValueError('HTTPS required')
    check_host(p.hostname)
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs): raise ValueError('Redirect not permitted')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect)
    req=urllib.request.Request(url,headers={'User-Agent':'APDIResearchBot/0.3 (reviewed sources)','Accept':accept})
    with opener.open(req,timeout=20) as resp:
        mime=resp.headers.get('Content-Type','').split(';')[0].strip().lower()
        data=resp.read(MAX_BYTES+1)
    if len(data)>MAX_BYTES: raise ValueError('Response too large')
    return mime,data

def suggest_links(base,html,limit=40):
    parser=Links(); parser.feed(html)
    found={}
    for href,label in parser.links:
        url=normalize_link(href,base)
        if url and url!=base and (any(word in (url+' '+label).lower() for word in KEYWORDS) or url.lower().endswith('.pdf')):
            found.setdefault(url,label or urlparse(url).path.rsplit('/',1)[-1])
        if len(found)>=limit: break
    return found

def scan(db:Session, source_key:str, fetcher=fetch_bytes):
    src=next((s for s in registry() if s['key']==source_key),None)
    if not src: raise ValueError('Unknown registry source')
    mime,raw=fetcher(src['url'])
    if mime!='text/html': raise ValueError('Registry landing page must be HTML')
    suggestions=suggest_links(src['url'],raw.decode('utf-8',errors='replace'))
    added=0
    for url,title in suggestions.items():
        if db.scalar(select(DiscoveryProposal.id).where(DiscoveryProposal.url==url)) is not None: continue
        db.add(DiscoveryProposal(parent_source_key=source_key,url=url,title=title[:300],status='proposed',created_at=utcnow())); added+=1
    db.add(DiscoveryEvent(proposal_id=None,action='scan',detail=f'{source_key}: {len(suggestions)} candidates, {added} new',created_at=utcnow()))
    db.commit()
    return {'source_key':source_key,'found':len(suggestions),'new_proposals':added}

def ingest(db:Session,proposal:DiscoveryProposal,fetcher=fetch_bytes):
    if proposal.status!='approved': raise ValueError('Proposal must be approved before ingestion')
    src=next((s for s in registry() if s['key']==proposal.parent_source_key),None)
    if not src or not allowed(proposal.url,src['url']): raise ValueError('URL no longer belongs to approved registry host')
    mime,raw=fetcher(proposal.url)
    if mime=='text/html': title,content=extract_html(raw,proposal.title)
    elif mime=='application/pdf' or (proposal.url.lower().endswith('.pdf') and mime=='application/octet-stream'):
        try:
            from pypdf import PdfReader
        except ImportError as exc: raise ValueError('PDF support requires pypdf (pip install pypdf)') from exc
        from io import BytesIO
        reader=PdfReader(BytesIO(raw),strict=False)
        if len(reader.pages)>40: raise ValueError('PDF exceeds 40-page limit')
        content=' '.join((p.extract_text() or '') for p in reader.pages)
        content=re.sub(r'\s+',' ',content).strip()[:40000]
        if len(content)<100: raise ValueError('PDF contains insufficient selectable text; scanned PDFs not supported')
        title=proposal.title
    else: raise ValueError('Only HTML and PDF supported')
    key='discovered-'+hashlib.sha256(proposal.url.encode()).hexdigest()[:32]
    digest=hashlib.sha256(content.encode()).hexdigest()
    prior=db.scalar(select(IngestionSnapshot).where(IngestionSnapshot.source_key==key,IngestionSnapshot.content_hash==digest))
    if prior: result='unchanged'; snapshot=prior
    else:
        snapshot=IngestionSnapshot(source_key=key,source_name=src['name'],url=proposal.url,title=title[:300],content_hash=digest,excerpt=content[:1500],body_text=content,review_status='pending',fetched_at=utcnow())
        db.add(snapshot); db.flush(); result='new_snapshot'
    proposal.last_snapshot_id=snapshot.id
    db.add(DiscoveryEvent(proposal_id=proposal.id,action='ingested',detail=f'{result} snapshot={snapshot.id}',created_at=utcnow()))
    db.commit()
    return {'result':result,'snapshot_id':snapshot.id,'review_status':'pending'}
