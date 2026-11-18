"""Conservative, read-only project intelligence: page table segmentation, identity hints,
financial reconciliation and dated evidence timeline. Never publishes or writes to DB.

Text layout is *not* a trustworthy representation of merged PDF cells. Candidate
amounts stay unassigned until a reviewer checks row, column and financial kind.
"""
from __future__ import annotations
import argparse
import json
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from .pdf_table_review import extract_pages
from .project_intelligence_batch import conflicts

HEADER = re.compile(r'\bIP\s+Name\s+Letter\s+No\b', re.I)
COMPONENT = re.compile(r'\b(?:water harvesting|roads?|storm water|drainage|power supply|culverts?|administrative|greenery|building|contingenc|sub.station|street lights?)\b', re.I)
ANCHOR = re.compile(r'(?<![A-Za-z])(?:(?:MSE\s*[- ]?\s*CDP)\s+)?(?:IP|JP)\s*[-–]?\s*([A-Za-z][A-Za-z-]{2,35})\b', re.I)
SERIAL = re.compile(r'^\s*(\d{1,2})\s+(?:(?:MSE\s*[- ]?\s*CDP)\s+)?(?:IP|JP)\s*[-–]?\s*([A-Za-z][A-Za-z-]{2,35})\b', re.I)
TOTAL = re.compile(r'\btotal\s*:', re.I)
UNIT = re.compile(r'(?:Rs\.?|INR|₹)\s*(?:in\s*)?lakhs?', re.I)
MONEY = re.compile(r'(?<![\w.])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{2})(?![\w.])')
DATE = re.compile(r'\b(20\d{2})-(\d{2})-(\d{2})\b')
STATUS = {'announced','mou_signed','approved','grounded','operational','delayed','cancelled'}

def clean(s): return re.sub(r'\s+', ' ', s).strip()
def identity_key(name):
    """A blocking hint, not an authoritative merge key."""
    s = clean(name).casefold()
    s = re.sub(r'\b(?:mse|cdp|industrial|park|project)\b', ' ', s)
    return re.sub(r'[^a-z0-9]', '', s)

def anchors_on_page(lines):
    anchors=[]
    for i,line in enumerate(lines):
        if HEADER.search(line): continue
        m = SERIAL.search(line)
        if not m:
            m = ANCHOR.search(line)
            if not m: continue
            # Prevent component rows with a project prefix being mistaken for project starts.
            remainder = line[m.end():m.end()+55]
            if COMPONENT.search(clean(m.group(1) + ' ' + remainder)) or COMPONENT.match(remainder.lstrip()): continue
        if COMPONENT.search(m.group(1)): continue
        name=clean(m.group(0))
        # Strip serial and preserve IP/JP prefix for readable project identity.
        name=re.sub(r'^\d{1,2}\s+', '', name)
        anchors.append({'line':i+1,'name':name,'key':identity_key(name),'serial':int(m.group(1)) if m.re is SERIAL else None,'text':clean(line)[:400]})
    # A serial anchor is stronger than unnumbered mentions. Other mentions are kept
    # for reviewer inspection but never permitted to steal a numbered block.
    return anchors

def inspect_tables(pages):
    results=[]; exclusions=[]
    for page in pages:
        lines=page['text'].splitlines(); anchors=anchors_on_page(lines)
        numbered=[a for a in anchors if a['serial'] is not None]
        for a in anchors:
            if a['serial'] is None and any(abs(a['line']-n['line'])<=2 and a['key']==n['key'] for n in numbered):
                continue
            # A numbered project row begins a candidate block. The next numbered
            # row ends it. An unnumbered row cannot establish ownership.
            next_serial=min((n['line'] for n in numbered if n['line']>a['line']),default=len(lines)+1)
            end=next_serial-1 if a['serial'] is not None else a['line']
            totals=[]
            for lineno in range(a['line'],end+1):
                line=lines[lineno-1]
                if TOTAL.search(line):
                    for amount_line in (lineno,lineno+1):
                        if amount_line>end: continue
                        tokens=MONEY.findall(lines[amount_line-1])
                        if tokens:
                            totals.append({'page':page['page'],'line':amount_line,'text':clean(lines[amount_line-1])[:450], 'tokens':tokens,'financial_kind':'unassigned','column_verified':False})
            flags=[]
            if a['serial'] is None: flags.append('no_numbered_project_boundary')
            if not any(UNIT.search(s) for s in lines[:min(len(lines),10)]): flags.append('unit_heading_not_detected')
            if not totals: flags.append('no_total_in_bounded_block')
            if any(x['line']>a['line'] and x['line']<=end and x['key']!=a['key'] for x in anchors): flags.append('other_project_mentions_inside_block')
            if totals: flags.append('financial_columns_unverified')
            results.append({'project_hint':a['name'],'identity_hint':a['key'],'serial':a['serial'],'page':page['page'],'start_line':a['line'],'end_line':end,'anchor_text':a['text'],'total_candidates':totals,'flags':flags,'review_state':'needs_visual_row_column_verification'})
        if not anchors: exclusions.append({'page':page['page'],'reason':'no_project_anchor'})
    return {'mode':'conservative_table_segmentation','project_mentions':len(results),'projects':results,'pages_without_anchors':exclusions,'verified_financial_assignments':0,'notice':'Layout-derived boundaries and financial tokens are review hints only. No financial column attribution, database changes or publication.'}

def identity_suggestions(candidates):
    """Only exact normalized-key groups; collisions require human review."""
    grouped=defaultdict(list)
    for c in candidates:
        title=str(c.get('title') or c.get('project_hint') or '')
        if title: grouped[identity_key(title)].append({'id':c.get('id'),'title':title,'district':c.get('district'),'snapshot_id':c.get('snapshot_id')})
    return [{'identity_hint':k,'members':v,'action':'review_only_no_auto_merge'} for k,v in sorted(grouped.items()) if k and len(v)>1]

def evidence_timeline(evidence):
    """Evidence dates are observations, not necessarily project milestone dates."""
    out=[]
    for e in evidence:
        observed=e.get('source_date')
        if not isinstance(observed,str): continue
        try: parsed=date.fromisoformat(observed)
        except ValueError: continue
        status=e.get('observed_status')
        if status not in STATUS: status=None
        out.append({'candidate_id':e.get('candidate_id'),'snapshot_id':e.get('snapshot_id'),'source_date':parsed.isoformat(),'observed_status':status,'quote':str(e.get('quote') or '')[:500],'classification':'source_observation_not_verified_milestone'})
    return sorted(out,key=lambda x:(x['source_date'],str(x['candidate_id']),str(x['snapshot_id'])))

def build_report(pages=None,candidates=None,financial_evidence=None,linked_evidence=None):
    report={'version':2,'mode':'read_only_no_db_writes'}
    if pages is not None: report['table_review']=inspect_tables(pages)
    if candidates is not None:
        report['identity_suggestions']=identity_suggestions(candidates)
        if financial_evidence is not None: report['financial_conflicts']=conflicts(candidates,financial_evidence)
    if linked_evidence is not None: report['evidence_timeline']=evidence_timeline(linked_evidence)
    return report

def main():
    parser=argparse.ArgumentParser(description='Read-only project intelligence v2 report')
    parser.add_argument('pdf',type=Path,nargs='?')
    parser.add_argument('--candidates',type=Path)
    parser.add_argument('--financial-evidence',type=Path)
    parser.add_argument('--linked-evidence',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not any((args.pdf,args.candidates,args.linked_evidence)): parser.error('Provide PDF and/or input JSON')
    def load(p):
        if p is None: return None
        data=json.loads(p.read_text(encoding='utf-8'))
        if not isinstance(data,list): parser.error(f'{p}: expected JSON array')
        return data
    report=build_report(extract_pages(args.pdf.read_bytes()) if args.pdf else None,load(args.candidates),load(args.financial_evidence),load(args.linked_evidence))
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Wrote read-only intelligence v2 report:',args.output)
if __name__=='__main__': main()
