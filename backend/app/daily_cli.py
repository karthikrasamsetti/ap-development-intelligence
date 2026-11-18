"""Run: python -m app.daily_cli [--force] [--no-scan] [approved-source-key ...]"""
import argparse
import json
from .db import SessionLocal
from .daily_intelligence import run_daily

def main(argv=None):
    parser = argparse.ArgumentParser(description='APDI daily source collection and link discovery')
    parser.add_argument('source_keys', nargs='*')
    parser.add_argument('--force', action='store_true', help='Ignore monitor polling interval')
    parser.add_argument('--no-scan', action='store_true', help='Skip link discovery')
    args = parser.parse_args(argv)
    with SessionLocal() as db:
        result = run_daily(db, keys=args.source_keys or None, force=args.force, scan_links=not args.no_scan)
    print(json.dumps(result, indent=2, default=str))
    return 1 if result['result'] != 'complete' or result.get('summary', {}).get('errors', 0) else 0

if __name__ == '__main__':
    raise SystemExit(main())
