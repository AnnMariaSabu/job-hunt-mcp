"""Where a job came from: find links in text and detect the job site.

We only READ the link text. We never download LinkedIn/Naukri pages (no scraping).
"""

import re
from urllib.parse import urlparse

# A web link: starts with http:// or https:// and runs until a space or bracket.
URL_PATTERN = re.compile(r"https?://[^\s<>\"'()\[\]]+")

SITE_DOMAINS = {
    "linkedin": ["linkedin.com"],
    "naukri": ["naukri.com"],
    "indeed": ["indeed.com", "indeed.co.in"],
}


def is_link(text: str) -> bool:
    """True if the whole text is just a link."""
    text = text.strip()
    return bool(URL_PATTERN.fullmatch(text))


def find_links(text: str) -> list[str]:
    """Every link inside some text, in order."""
    return [m.rstrip(".,;:!") for m in URL_PATTERN.findall(text)]


def detect_source(link: str) -> str:
    """'linkedin', 'naukri', 'indeed' or 'other', based on the link's website."""
    if not link:
        return "other"
    host = urlparse(link).netloc.lower()
    for source, domains in SITE_DOMAINS.items():
        if any(host == d or host.endswith("." + d) for d in domains):
            return source
    return "other"
