
"""Explainable, deterministic discovery triage.

Scores are advisory and are not evidence verification.
"""

import re
from difflib import SequenceMatcher
from urllib.parse import unquote, urlparse


POSITIVE = (
    ("project status", 38, "Project implementation status"),
    ("projects-status", 38, "Project implementation status"),
    ("progress report", 36, "Project progress report"),
    ("memorandum of understanding", 32, "MoU documentation"),
    ("industrial park", 32, "Industrial park"),
    ("industrial cluster", 30, "Industrial cluster"),
    ("investment", 28, "Investment information"),
    ("infrastructure", 27, "Infrastructure information"),
    ("project", 23, "Project information"),
    ("mou", 24, "MoU documentation"),
    ("land parcel", 24, "Industrial land information"),
    ("port", 17, "Port-related information"),
    ("msme", 17, "MSME development"),
    ("mse cdp", 28, "Cluster development programme"),
    ("development", 16, "Development information"),
    ("annual report", 14, "Annual report"),
    ("tender", 9, "Tender documentation"),
)

NEGATIVE = (
    ("contact", -45, "Contact directory"),
    ("commissioner", -32, "Administrative contact listing"),
    ("empanel", -32, "Vendor/consultant empanelment"),
    ("policy", -18, "General policy document"),
    ("sexual harassment", -70, "Unrelated internal policy"),
    ("csr", -35, "CSR administration"),
    ("format", -36, "Document template"),
    ("sale deed", -42, "Document template"),
    ("agreement for sale", -36, "Document template"),
    ("noc", -22, "Administrative form"),
    ("old tender", -28, "Archive rather than current project evidence"),
    ("rate contract", -34, "Procurement contract"),
    ("category a", -12, "Unclear category document"),
    ("category b", -12, "Unclear category document"),
    ("category c", -12, "Unclear category document"),
    ("category d", -12, "Unclear category document"),
    ("category e", -12, "Unclear category document"),
)

TEMPLATE_TERMS = (
    "checklist",
    "template",
    "dpr component",
    "components of detailed project report",
    "format for",
    "sample form",
    "application form",
)

DIRECTORY_TERMS = (
    "contact details",
    "phone directory",
    "commissioners",
    "contact list",
)


def clean(value: str) -> str:
    value = unquote(value or "").lower()
    value = value.replace("-", " ").replace("_", " ")
    return re.sub(
        r"\s+",
        " ",
        re.sub(r"[^a-z0-9]+", " ", value),
    ).strip()


def matches(text: str, term: str) -> bool:
    """Match whole words or phrases, not substrings of words."""
    normalized = clean(term)
    if not normalized:
        return False

    pattern = rf"(?<!\w){re.escape(normalized)}(?!\w)"
    return bool(re.search(pattern, text))


def document_class(title: str, url: str) -> str:
    path = urlparse(url).path
    text = clean(f"{title} {path}")

    if any(matches(text, term) for term in DIRECTORY_TERMS):
        return "directory"

    if any(matches(text, term) for term in TEMPLATE_TERMS):
        return "template"

    if any(matches(text, term) for term in (
        "project status",
        "projects status",
        "progress report",
    )):
        return "project_status"

    if matches(text, "memorandum of understanding") or matches(text, "mou"):
        return "mou"

    if matches(text, "annual report"):
        return "annual_report"

    if matches(text, "industrial park") or matches(text, "industrial cluster"):
        return "industrial_infrastructure"

    if matches(text, "tender"):
        return "tender"

    if matches(text, "project") or matches(text, "investment"):
        return "project_information"

    return "general"


def assess(title: str, url: str) -> dict:
    path = urlparse(url).path
    haystack = clean(f"{title} {path}")

    score = 20
    reasons = []
    seen = set()

    for term, points, reason in POSITIVE + NEGATIVE:
        if matches(haystack, term) and reason not in seen:
            score += points
            reasons.append(reason)
            seen.add(reason)

    classification = document_class(title, url)

    # Templates may mention projects without documenting actual progress.
    if classification == "template":
        score -= 35
        reasons.append("Generic template; not project implementation evidence")

    if classification == "directory":
        score -= 30
        reasons.append("Directory; not project implementation evidence")

    score = max(0, min(100, score))

    priority = (
        "high" if score >= 65
        else "medium" if score >= 40
        else "low"
    )

    return {
        "score": score,
        "priority": priority,
        "reasons": list(dict.fromkeys(reasons))[:8],
        "document_type": (
            "pdf" if path.lower().endswith(".pdf") else "html"
        ),
        "document_class": classification,
        "review_required": True,
    }


def duplicate_hints(
    proposals: list,
    threshold: float = 0.91,
) -> dict[int, list[int]]:
    """Flag similar titles within a source without merging records."""
    results = {proposal.id: [] for proposal in proposals}
    groups = {}

    for proposal in proposals:
        groups.setdefault(
            proposal.parent_source_key, []
        ).append(proposal)

    for group in groups.values():
        for index, first in enumerate(group):
            first_title = clean(first.title)

            if len(first_title) < 15:
                continue

            for second in group[index + 1:]:
                second_title = clean(second.title)

                if len(second_title) < 15:
                    continue

                similarity = SequenceMatcher(
                    None, first_title, second_title
                ).ratio()

                if similarity >= threshold:
                    results[first.id].append(second.id)
                    results[second.id].append(first.id)

    return results
