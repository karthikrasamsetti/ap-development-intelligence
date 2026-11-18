"""Advisory cross-snapshot project-title similarity; never merges or publishes."""
import re
from difflib import SequenceMatcher


def normalize_title(value: str) -> str:
    text = (value or '').casefold()
    text = re.sub(r'(?<=\D)\d{1,2}$', '', text.strip())
    text = re.sub(r'\b(?:mse[ -]?cdp|industrial park|ip)\b', ' ', text)
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]+', ' ', text)).strip()


def cross_snapshot_suggestions(candidate, others, threshold: float = 0.88) -> list[dict]:
    target = normalize_title(candidate.title)
    if len(target) < 5:
        return []
    matches = []
    for other in others:
        if other.id == candidate.id or other.snapshot_id == candidate.snapshot_id:
            continue
        comparable = normalize_title(other.title)
        if len(comparable) < 5:
            continue
        similarity = SequenceMatcher(None, target, comparable).ratio()
        if similarity >= threshold:
            matches.append({
                'id': other.id,
                'snapshot_id': other.snapshot_id,
                'title': other.title,
                'review_status': other.review_status,
                'similarity': round(similarity, 3),
            })
    return sorted(matches, key=lambda x: x['similarity'], reverse=True)[:20]
