# Explicit allowlist: ingestion never crawls arbitrary links.
SOURCES = [
    {"key": "apiic-home", "name": "Andhra Pradesh Industrial Infrastructure Corporation", "url": "https://apiic.in/", "kind": "government", "scope": "industrial infrastructure", "district": None},
    {"key": "prakasam-invest", "name": "Prakasam District Investment Portal", "url": "https://prakasam.ap.gov.in/invest-in-prakasam/", "kind": "government", "scope": "investment projects", "district": "Prakasam"},
]
