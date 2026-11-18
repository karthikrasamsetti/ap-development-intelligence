"""Conservative source snapshot ingestion. No AI extraction or automatic publication."""
import hashlib
import re
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlparse
from sqlalchemy import select
from .db import SessionLocal
from .models import IngestionSnapshot
from .source_registry import SOURCES

MAX_BYTES = 1_500_000
class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.skip=0; self.in_title=False; self.title=[]; self.words=[]
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style','noscript'): self.skip += 1
        if tag == 'title': self.in_title=True
    def handle_endtag(self, tag):
        if tag in ('script','style','noscript'): self.skip=max(0,self.skip-1)
        if tag == 'title': self.in_title=False
    def handle_data(self, data):
        if self.in_title: self.title.append(data)
        if not self.skip: self.words.append(data)

def ingest_source(key: str):
    src = next((x for x in SOURCES if x['key']==key), None)
    if not src: raise ValueError('Unknown source key')
    parsed=urlparse(src['url'])
    if parsed.scheme != 'https' or not parsed.hostname: raise ValueError('HTTPS source required')
    request=urllib.request.Request(src['url'], headers={'User-Agent':'APDIResearchBot/0.1 (+public information research)', 'Accept':'text/html'})
    # No redirects to unapproved hosts: avoid unexpected destinations.
    class SafeRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            dest=urlparse(newurl)
            if dest.scheme != 'https' or dest.hostname != parsed.hostname: raise ValueError('Redirect outside approved source host')
            return super().redirect_request(req, fp, code, msg, headers, newurl)
    opener=urllib.request.build_opener(SafeRedirect)
    with opener.open(request, timeout=20) as response:
        if 'text/html' not in response.headers.get('Content-Type','').lower(): raise ValueError('Expected HTML response')
        raw=response.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES: raise ValueError('Source exceeded size limit')
    parser=PageParser(); parser.feed(raw.decode('utf-8',errors='replace'))
    content=re.sub(r'\s+',' ',' '.join(parser.words)).strip()[:40000]
    title=re.sub(r'\s+',' ',' '.join(parser.title)).strip()[:300] or src['name']
    if len(content)<100: raise ValueError('Insufficient extracted content; check page manually')
    digest=hashlib.sha256(content.encode('utf-8')).hexdigest()
    with SessionLocal() as db:
        previous=db.scalar(select(IngestionSnapshot).where(IngestionSnapshot.source_key==key, IngestionSnapshot.content_hash==digest))
        if previous: return {'result':'unchanged','snapshot_id':previous.id,'source_key':key}
        row=IngestionSnapshot(source_key=key,source_name=src['name'],url=src['url'],title=title,content_hash=digest,excerpt=content[:1500],body_text=content,review_status='pending',fetched_at=datetime.now(timezone.utc))
        db.add(row); db.commit(); db.refresh(row)
        return {'result':'queued_for_review','snapshot_id':row.id,'source_key':key,'title':title}

def ingest_all():
    output=[]
    for source in SOURCES:
        try: output.append(ingest_source(source['key']))
        except Exception as exc: output.append({'source_key':source['key'],'result':'error','message':str(exc)})
    return output

if __name__=='__main__':
    import json, sys
    result=ingest_all() if len(sys.argv)==1 or sys.argv[1]=='all' else ingest_source(sys.argv[1])
    print(json.dumps(result,indent=2))
