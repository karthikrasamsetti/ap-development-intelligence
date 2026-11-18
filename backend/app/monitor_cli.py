"""Usage: python -m app.monitor_cli [source-key ...] [--force].
Use an external scheduler, e.g. cron, to invoke this command periodically.
"""
import json
import sys
from .db import SessionLocal
from .source_monitor import run_monitor

def main():
    args=sys.argv[1:]; force='--force' in args; keys=[x for x in args if x!='--force']
    with SessionLocal() as db:
        result=run_monitor(db,keys=keys or None,force=force)
    print(json.dumps(result,indent=2))
    if result['result']=='already_running': return 0
    return 1 if any(x['result']=='error' for x in result['sources']) else 0

if __name__=='__main__': sys.exit(main())
