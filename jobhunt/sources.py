"""Where a job came from: links, job sites, and job-alert emails.

We only READ text that I paste. We never download LinkedIn/Naukri pages (no scraping).
"""

import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

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


# ---------- cleaning links ----------

TRACKING_PARAMS = {"trackingid", "refid", "trk", "src", "from", "lipi", "midtoken",
                   "midsig", "eid", "otptoken", "sid", "xid", "alertid"}


def normalize_link(link: str) -> str:
    """One standard form per job, so duplicates are caught.

    linkedin.com/comm/jobs/view/123/?trackingId=x -> https://www.linkedin.com/jobs/view/123/
    in.indeed.com/rc/clk?jk=abc&from=ja           -> https://in.indeed.com/viewjob?jk=abc
    naukri.com/job-listings-x-123?src=jobalert    -> https://www.naukri.com/job-listings-x-123
    """
    link = (link or "").strip()
    if not link:
        return ""
    parts = urlparse(link)
    host = parts.netloc.lower()
    query = parse_qs(parts.query)
    source = detect_source(link)

    if source == "linkedin":
        found = re.search(r"/jobs/view/(?:[^/]*-)?(\d+)", parts.path)
        job_id = found.group(1) if found else (query.get("currentJobId") or [None])[0]
        if job_id:
            return f"https://www.linkedin.com/jobs/view/{job_id}/"
    if source == "indeed" and query.get("jk"):
        return f"https://{host}/viewjob?jk={query['jk'][0]}"
    if source == "naukri":
        return urlunparse(("https", "www.naukri.com", parts.path, "", "", ""))

    # Any other site: drop tracking parameters (utm_..., trk, ...) and the #fragment.
    kept = {k: v for k, v in query.items()
            if not k.lower().startswith("utm_") and k.lower() not in TRACKING_PARAMS}
    return urlunparse((parts.scheme, host, parts.path, "", urlencode(kept, doseq=True), ""))


def is_job_link(link: str) -> bool:
    """True for links that point to ONE job (not 'unsubscribe', 'settings', ...)."""
    source = detect_source(link)
    path_and_query = link.lower()
    if source == "linkedin":
        return "/jobs/view/" in path_and_query or "currentjobid=" in path_and_query
    if source == "naukri":
        return "job-listings" in path_and_query
    if source == "indeed":
        return "jk=" in path_and_query
    return False


# ---------- job-alert emails ----------

# Lines in alert emails that are buttons or noise, not job details.
NOISE = re.compile(
    r"^(your job alert|jobs you may|based on your|top job picks|"
    r"view job|apply( now)?|easy apply|see all|see more|unsubscribe|promoted|"
    r"actively recruiting|be an early applicant|new jobs?|job alert|jobs? for you|"
    r"\d+ (new )?jobs?|recommended|hi\b|hello\b)", re.IGNORECASE)

# Bits of a line that are salary / experience / dates, not role, company or place.
EXTRA = re.compile(r"(₹|\brs\.?\s*\d|\blpa\b|a year|per annum|\byrs?\b|\byears?\b|"
                   r"\bexp\b|posted|\bago\b|applicants?)", re.IGNORECASE)


def clean_detail(line: str) -> str:
    """'2-5 Yrs | Chennai' -> 'Chennai'.  '₹6,00,000 a year' -> ''."""
    parts = [p.strip() for p in re.split(r"\s*[|•·]\s*", line)]
    return ", ".join(p for p in parts if p and not EXTRA.search(p))


def parse_job_alerts(email_text: str) -> list[dict]:
    """Find jobs in a pasted job-alert email (LinkedIn / Naukri / Indeed).

    Most alerts look like this, so we read the lines ABOVE each job link:
        Data Analyst                  <- role
        Acme Corp                     <- company
        Bengaluru, Karnataka          <- location
        View job: https://www.linkedin.com/comm/jobs/view/123/
    It's a simple guess. Claude can fix any field afterwards with update_job_details.
    """
    jobs, seen, block = [], set(), []
    for raw in (email_text or "").splitlines():
        line = raw.strip()
        links = find_links(line)
        job_links = [link for link in links if is_job_link(link)]
        if not job_links:
            text = line.strip(" :|-•·")
            if text and not links and not NOISE.match(text):
                text = clean_detail(text)
                if text:
                    block.append(text)
            continue
        link = normalize_link(job_links[0])
        details = block[-3:]  # the (up to) 3 detail lines right above the link
        block = []
        if link in seen:
            continue
        seen.add(link)
        role, company, location = (details + ["", "", ""])[:3]
        if not location and " - " in company:  # "Gamma Tech - Kochi, Kerala"
            company, location = (part.strip() for part in company.split(" - ", 1))
        jobs.append({"role": role, "company": company, "location": location,
                     "link": link, "source": detect_source(link)})
    return jobs
