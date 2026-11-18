"""Daily collection orchestration; never approves, extracts or publishes claims."""
from datetime import datetime, timezone
from sqlalchemy import text
from .source_monitor import run_monitor, registry
from .discovery import scan

DAILY_LOCK = 738291116

def run_daily(db, *, keys=None, force=False, scan_links=True, monitor_runner=run_monitor, scanner=scan):
    sources = registry()
    allowed = {s['key'] for s in sources}
    if keys:
        unknown = set(keys) - allowed
        if unknown:
            raise ValueError('Unknown source keys: ' + ', '.join(sorted(unknown)))
        sources = [s for s in sources if s['key'] in keys]
    started = datetime.now(timezone.utc).isoformat()
    locked = bool(db.scalar(text('SELECT pg_try_advisory_lock(:lock)'), {'lock': DAILY_LOCK}))
    if not locked:
        return {'result': 'already_running', 'started_at': started, 'sources': [], 'discovery': []}
    try:
        monitored = monitor_runner(db, keys=[s['key'] for s in sources], force=force)
        discovered = []
        if scan_links and monitored['result'] != 'already_running':
            for source in sources:
                key = source['key']
                try:
                    outcome = scanner(db, key)
                    discovered.append({'source_key': key, 'result': 'ok', **outcome})
                except Exception as exc:
                    db.rollback()
                    discovered.append({'source_key': key, 'result': 'error', 'error_type': type(exc).__name__})
        errors = sum(x.get('result') == 'error' for x in monitored.get('sources', [])) + sum(x['result'] == 'error' for x in discovered)
        return {'result': 'complete' if monitored['result'] == 'complete' else monitored['result'],
                'started_at': started, 'finished_at': datetime.now(timezone.utc).isoformat(),
                'sources': monitored['sources'], 'discovery': discovered,
                'summary': {'sources_checked': len(monitored['sources']),
                            'new_snapshots': sum(x.get('result') == 'new_snapshot' for x in monitored['sources']),
                            'new_link_proposals': sum(x.get('new_proposals', 0) for x in discovered),
                            'errors': errors},
                'notice': 'Collection and discovery only; no automatic approval, extraction, or publication.'}
    finally:
        db.execute(text('SELECT pg_advisory_unlock(:lock)'), {'lock': DAILY_LOCK})
        db.commit()
