"""Deterministic safeguards for untrusted LLM extraction. No database writes."""
import re
from decimal import Decimal, InvalidOperation

_BAD_START = re.compile(r'^(?:with\s+an?\s+|parameter\s+details\b|strategically\s+located\b|the\s+proposed\s+investments\b|project\s+highlights\b|\d+\s*,\s*infrastructure\b)', re.I)
_BAD_TAIL = re.compile(r'(?:[A-Za-z]{3,})\d{1,2}$')

def good_project_name(name):
    name = (name or '').strip()
    return (8 <= len(name) <= 110 and len(name.split()) <= 14
            and not _BAD_START.search(name) and not _BAD_TAIL.search(name)
            and not re.search(r'\b(?:parameter\s+details|see\s+more|total\s+area|nearest\s+city)\b', name, re.I))

def exact_excerpt(text, quote):
    return bool(isinstance(quote, str) and len(quote.strip()) >= 10 and quote.strip() in (text or ''))

def _number_pairs(text):
    # Reject partial numbers and units embedded inside longer tokens.
    for match in re.finditer(r'(?<![\w.,])([0-9][\d,]*(?:\.\d+)?)\s*(lakh\s*crores?|crores?|cr\.?)\b', text or '', re.I):
        try:
            raw = Decimal(match.group(1).replace(',', ''))
            yield raw * (100000 if match.group(2).lower().startswith('lakh') else 1)
        except InvalidOperation:
            continue

def supported_investment(value, quote, text):
    if value is None:
        return True
    if not exact_excerpt(text, quote):
        return False
    try:
        target = Decimal(str(value))
    except InvalidOperation:
        return False
    if any(abs(v - target) <= Decimal('0.01') for v in _number_pairs(quote)):
        return True
    # PDF table excerpts are accepted only with an explicit crore heading,
    # a single numeric cell, and no competing amount.
    if len(quote) > 180 or not re.search(r'\b(?:investment|project\s+cost|estimated\s+cost|amount)\s*(?:\([^)]*\)\s*)?(?:in\s+)?(?:₹|rs\.?|inr)?\s*(?:crores?|cr\.?)\b', quote, re.I):
        return False
    nums = re.findall(r'(?<![\w.,])\d[\d,]*(?:\.\d+)?(?![\w.,])', quote)
    try:
        return len(nums) == 1 and abs(Decimal(nums[0].replace(',', '')) - target) <= Decimal('0.01')
    except InvalidOperation:
        return False

def supported_jobs(value, quote, text, *, realized=False):
    if value is None:
        return True
    if not exact_excerpt(text, quote):
        return False
    if not re.search(r'\b(?:jobs?|employment|employees?|workforce|people\s+employed)\b', quote, re.I):
        return False
    if realized and not re.search(r'\b(?:created|employed|on\s+payroll|currently\s+employs|jobs\s+generated)\b', quote, re.I):
        return False
    nums = re.findall(r'(?<![\w.,])\d[\d,]*(?![\w.,])', quote)
    return any(int(n.replace(',', '')) == value for n in nums)
