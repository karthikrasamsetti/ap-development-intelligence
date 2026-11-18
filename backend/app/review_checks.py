"""Conservative advisory checks; never treat a warning as independent fact verification."""
import json
import re
from decimal import Decimal, InvalidOperation

STOP = {"the", "and", "for", "with", "project", "development", "limited", "ltd", "of", "at", "in", "a", "an", "proposed", "integrated", "industrial"}
# Programme/type words identify a scheme, not a particular industrial park.
GENERIC = STOP | {"mse", "cdp", "msme", "ip", "park", "scheme", "phase", "cluster", "mega", "hub", "andhra", "pradesh"}


def tokens(value):
    return set(re.findall(r"[a-z0-9]+", (value or "").lower())) - STOP


def identity_tokens(value):
    value = re.sub(r"(?<=\D)(?=\d\b)", " ", value or "")
    return tokens(value) - GENERIC


def similar_names(a, b):
    x, y = identity_tokens(a), identity_tokens(b)
    if not x or not y:
        return False
    if x == y:
        return True
    # Legacy extraction can append a whole paragraph to the same project title.
    # Require a contiguous full-name prefix, not just shared scheme words.
    shorter, longer = sorted((a or "", b or ""), key=len)
    if len(shorter.strip()) >= 16 and re.match(r"^" + re.escape(shorter.strip()) + r"(?:\b|\s)", longer.strip(), re.I):
        return True
    # Do not flag a different named site because its programme prefix matches.
    return len(x & y) >= 2 and len(x & y) / max(len(x), len(y)) >= 0.8


def duplicate_suggestions(candidate, others):
    return [
        {"id": other.id, "title": other.title, "review_status": other.review_status}
        for other in others
        if other.id != candidate.id and other.review_status != "rejected"
        and similar_names(candidate.title, other.title)
    ]


def quote_in(text, quote):
    return bool(quote and quote.strip() and quote.strip() in (text or ""))


def _numbers(evidence):
    for match in re.finditer(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w.])", evidence):
        try:
            yield Decimal(match.group().replace(",", ""))
        except InvalidOperation:
            continue


def numeric_supported(value, evidence, source_text, kind):
    if value is None:
        return True
    if not quote_in(source_text, evidence):
        return False
    target = Decimal(str(value))
    if kind == "investment":
        # Explicit value-unit pairs, e.g. "13.79 crore" or "1 lakh crore".
        pattern = r"(?<!\w)([\d,]+(?:\.\d+)?)\s*(lakh[\s-]*crore|crores?|cr\.?)(?!\w)"
        for raw, unit in re.findall(pattern, evidence, re.I):
            try:
                amount = Decimal(raw.replace(",", ""))
                if unit.lower().startswith("lakh"):
                    amount *= 100000
                if abs(amount - target) <= Decimal("0.01"):
                    return True
            except InvalidOperation:
                continue
        # PDF tables sometimes put the unit in the column heading.
        # Accept only an explicit currency/INR crore heading and a unique
        # numeric value in the same short excerpt; ambiguous rows are rejected.
        heading = re.search(r"(?:investment|project\s+cost|estimated\s+cost|amount)\s*(?:\(\s*)?(?:₹|rs\.?|inr)?\s*(?:in\s*)?(?:₹|rs\.?|inr)?\s*(?:crores?|cr\.?)\b", evidence, re.I)
        if heading and len(evidence) <= 180:
            numbers = list(_numbers(evidence))
            return len(numbers) == 1 and abs(numbers[0] - target) <= Decimal("0.01")
        return False
    if not re.search(r"\b(?:jobs?|employment|employees?|people\s+employed|workforce)\b", evidence, re.I):
        return False
    return any(n == target for n in _numbers(evidence))


def title_warnings(title):
    title = (title or "").strip()
    problems = []
    if len(title) > 120 or len(title.split()) > 16:
        problems.append("Project title looks like a paragraph or PDF table fragment; replace with a concise source-supported project name")
    if re.match(r"^(?:with\s+an?\s+|parameter\s+details\b|strategically\s+located\b|the\s+proposed\s+investments\b|\d+\s*,\s*infrastructure\b)", title, re.I):
        problems.append("Project title starts with narrative or table text; verify the actual project identity")
    if re.search(r"[A-Za-z][#]\d+$", title) or re.search(r"(?:[A-Za-z]{3,})\d{1,2}$", title):
        problems.append("Project title may contain a PDF row-number artifact; verify against source")
    return problems


def field_warnings(candidate, source_text):
    issues = title_warnings(getattr(candidate, "title", ""))
    if not quote_in(source_text, candidate.evidence_quote):
        issues.append("Primary evidence quote is not an exact excerpt of the snapshot")
    try:
        evidence = json.loads(candidate.field_evidence or "{}")
        if not isinstance(evidence, dict):
            evidence = {}
    except (ValueError, TypeError):
        evidence = {}
    for field, evidence_field, kind in (
        ("investment_inr_crore", "investment_evidence", "investment"),
        ("expected_jobs", "expected_jobs_evidence", "jobs"),
        ("jobs_created", "jobs_created_evidence", "jobs"),
    ):
        value = getattr(candidate, field)
        if value is not None and not numeric_supported(value, evidence.get(evidence_field), source_text, kind):
            issues.append(f"{field} lacks an exact matching number/unit in saved field evidence; clear or correct it")
    if candidate.status == "unknown":
        issues.append("Project status is unknown; select a source-supported status")
    elif candidate.extraction_method == "llm" and not quote_in(source_text, evidence.get("status_evidence")):
        issues.append("Project status lacks a supporting source excerpt")
    if candidate.district and candidate.extraction_method == "llm" and not quote_in(source_text, evidence.get("district_evidence")):
        issues.append("District lacks a supporting source excerpt")
    return issues
