from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
import httpx
from ..models import AuthorRecord, JournalMetrics, JournalRecord, JournalSummary, PaperRecord
from ..utils import clean_doi

CROSSREF_BASE = "https://api.crossref.org/v1"


def _strip_jats(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    cleaned = re.sub(r"<[^>]+>", " ", raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or None


def _parse_crossref_work(item: Dict[str, Any]) -> PaperRecord:
    doi = clean_doi(item.get("DOI"))
    titles = item.get("title") or []
    title = titles[0] if titles else "Untitled"

    authors: List[AuthorRecord] = []
    for a in item.get("author") or []:
        given = a.get("given") or ""
        family = a.get("family") or a.get("name") or ""
        full_name = f"{given} {family}".strip()
        if not full_name:
            continue
        orcid = (a.get("ORCID") or "").replace("http://orcid.org/", "").replace("https://orcid.org/", "") or None
        affs = [af.get("name") for af in (a.get("affiliation") or []) if af.get("name")]
        authors.append(AuthorRecord(name=full_name, orcid=orcid, affiliations=affs))

    pub_date_parts = (
        (item.get("published-print") or {}).get("date-parts")
        or (item.get("published-online") or {}).get("date-parts")
        or (item.get("issued") or {}).get("date-parts")
        or []
    )
    year: Optional[int] = None
    pub_date: Optional[str] = None
    if pub_date_parts and pub_date_parts[0]:
        parts = pub_date_parts[0]
        if len(parts) >= 1 and isinstance(parts[0], int):
            year = parts[0]
        pub_date = "-".join(f"{p:02d}" if idx > 0 else str(p) for idx, p in enumerate(parts))

    containers = item.get("container-title") or []
    issns = item.get("ISSN") or []
    journal = (
        JournalSummary(
            name=containers[0],
            issn_l=issns[0] if issns else None,
            issns=issns,
            publisher=item.get("publisher"),
        )
        if containers
        else None
    )

    pdf_url: Optional[str] = None
    for link in item.get("link") or []:
        if link.get("content-type") == "application/pdf" and link.get("URL"):
            pdf_url = link.get("URL")
            break

    return PaperRecord(
        id=f"doi:{doi}" if doi else "crossref:unknown",
        title=title,
        doi=doi,
        authors=authors,
        year=year,
        publication_date=pub_date,
        publication_type=item.get("type"),
        journal=journal,
        volume=item.get("volume"),
        issue=item.get("issue"),
        pages=item.get("page"),
        abstract=_strip_jats(item.get("abstract")),
        citation_count=item.get("is-referenced-by-count"),
        reference_count=item.get("references-count"),
        pdf_url=pdf_url,
        landing_page_url=item.get("URL") or (f"https://doi.org/{doi}" if doi else None),
        fields_of_study=item.get("subject") or [],
        source_providers=["crossref"],
    )


async def search_works_crossref(
    client: httpx.AsyncClient,
    query: str,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    issn: Optional[str] = None,
    limit: int = 10,
    mailto: str = "research-agent@example.org",
) -> List[PaperRecord]:
    params: Dict[str, Any] = {
        "query.bibliographic": query,
        "rows": min(max(limit, 1), 50),
        "mailto": mailto,
    }
    filters: List[str] = []
    if year_min:
        filters.append(f"from-pub-date:{year_min}")
    if year_max:
        filters.append(f"until-pub-date:{year_max}")
    if issn:
        filters.append(f"issn:{issn}")
    if filters:
        params["filter"] = ",".join(filters)

    resp = await client.get(f"{CROSSREF_BASE}/works", params=params, timeout=15.0)
    resp.raise_for_status()
    items = (resp.json().get("message") or {}).get("items") or []
    return [_parse_crossref_work(it) for it in items[:limit]]


async def get_work_crossref(
    client: httpx.AsyncClient,
    doi: str,
    mailto: str = "research-agent@example.org",
) -> Optional[PaperRecord]:
    cleaned = clean_doi(doi)
    if not cleaned:
        return None
    resp = await client.get(
        f"{CROSSREF_BASE}/works/{cleaned}",
        params={"mailto": mailto},
        timeout=12.0,
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    msg = resp.json().get("message")
    return _parse_crossref_work(msg) if msg else None


async def search_journals_crossref(
    client: httpx.AsyncClient,
    query: Optional[str] = None,
    issn: Optional[str] = None,
    limit: int = 10,
    mailto: str = "research-agent@example.org",
) -> List[JournalRecord]:
    params: Dict[str, Any] = {"mailto": mailto, "rows": min(max(limit, 1), 50)}
    if issn and not query:
        resp = await client.get(f"{CROSSREF_BASE}/journals/{issn}", params={"mailto": mailto}, timeout=12.0)
        if resp.status_code == 200:
            msg = resp.json().get("message") or {}
            return [_parse_crossref_journal(msg)]
    if query:
        params["query"] = query
    resp = await client.get(f"{CROSSREF_BASE}/journals", params=params, timeout=12.0)
    if resp.status_code != 200:
        return []
    items = (resp.json().get("message") or {}).get("items") or []
    return [_parse_crossref_journal(it) for it in items[:limit]]


def _parse_crossref_journal(msg: Dict[str, Any]) -> JournalRecord:
    issns = msg.get("ISSN") or []
    counts = msg.get("counts") or {}
    subjects = [s.get("name") for s in (msg.get("subjects") or []) if isinstance(s, dict) and s.get("name")]
    return JournalRecord(
        id=f"crossref:{issns[0]}" if issns else f"crossref:{msg.get('title', 'journal')}",
        title=msg.get("title") or "Unknown Journal",
        issn_l=issns[0] if issns else None,
        issns=issns,
        publisher=msg.get("publisher"),
        metrics=JournalMetrics(works_count=counts.get("total-dois")),
        topics=subjects,
        source_providers=["crossref"],
    )


async def fetch_doi_bibtex(client: httpx.AsyncClient, doi: str) -> Optional[str]:
    """Resolves official publisher/registration BibTeX via universal DOI content negotiation."""
    cleaned = clean_doi(doi)
    if not cleaned:
        return None
    resp = await client.get(
        f"https://doi.org/{cleaned}",
        headers={"Accept": "application/x-bibtex; charset=utf-8"},
        follow_redirects=True,
        timeout=12.0,
    )
    if resp.status_code == 200 and "@" in resp.text:
        return resp.text.strip()
    return None
