from __future__ import annotations
import asyncio
import io
import json
import re
from typing import Any, Dict, List, Optional, Tuple
import httpx
from pypdf import PdfReader
from ..models import (
    AuthorRecord,
    CitationEdge,
    ContextSnippet,
    JournalRecord,
    JournalSummary,
    PaperRecord,
)
from ..utils import clean_arxiv_id, clean_doi

DOAJ_BASE = "https://doaj.org/api/v4"
DBLP_BASE = "https://dblp.org/search"
INSPIRE_BASE = "https://inspirehep.net/api"
UNPAYWALL_BASE = "https://api.unpaywall.org/v2"
OPENCITATIONS_BASE = "https://api.opencitations.net/index/v2"

_DBLP_COOKIES: httpx.Cookies = httpx.Cookies()
_DBLP_LOCK = asyncio.Lock()


async def _dblp_get_with_anubis(
    client: httpx.AsyncClient,
    url: str,
    params: Optional[Dict[str, Any]] = None,
) -> httpx.Response:
    """
    Handles DBLP's Anubis v1.27.0 metarefresh challenge (HTTP 202) transparently
    and caches the resulting dblp.org auth cookie for subsequent requests.
    """
    global _DBLP_COOKIES
    client.cookies.update(_DBLP_COOKIES)
    resp = await client.get(url, params=params, follow_redirects=True, timeout=14.0)
    if resp.status_code != 202 or "anubis_challenge" not in resp.text:
        return resp

    async with _DBLP_LOCK:
        client.cookies.update(_DBLP_COOKIES)
        resp = await client.get(url, params=params, follow_redirects=True, timeout=14.0)
        if resp.status_code != 202 or "anubis_challenge" not in resp.text:
            return resp
        m = re.search(r'<script id="anubis_challenge" type="application/json">(.*?)</script>', resp.text, re.S)
        if not m:
            return resp
        ch = json.loads(m.group(1)).get("challenge") or {}
        if not ch.get("id") or not ch.get("randomData"):
            return resp
        await asyncio.sleep(1.08)
        pass_resp = await client.get(
            "https://dblp.org/.within.website/x/cmd/anubis/api/pass-challenge",
            params={
                "id": ch["id"],
                "challenge": ch["randomData"],
                "redir": str(resp.url),
            },
            follow_redirects=True,
            timeout=14.0,
        )
        _DBLP_COOKIES.update(client.cookies)
        return pass_resp


async def search_journals_doaj(
    client: httpx.AsyncClient,
    query: Optional[str] = None,
    issn: Optional[str] = None,
    limit: int = 10,
) -> List[JournalRecord]:
    search_term = f'issn:"{issn}"' if issn and not query else (query or "*")
    encoded_q = search_term.replace("/", "%5C/")
    url = f"{DOAJ_BASE}/search/journals/{encoded_q}"
    resp = await client.get(url, params={"pageSize": min(max(limit, 1), 50)}, timeout=12.0)
    if resp.status_code != 200:
        return []
    results = resp.json().get("results") or []
    journals: List[JournalRecord] = []
    for r in results[:limit]:
        bib = r.get("bibjson") or {}
        pissn = bib.get("pissn")
        eissn = bib.get("eissn")
        issns = [i for i in (pissn, eissn) if i]
        apc_obj = bib.get("apc") or {}
        apc_usd: Optional[int] = None
        if apc_obj.get("has_apc") and apc_obj.get("max"):
            for m in apc_obj["max"]:
                if m.get("currency") == "USD" and isinstance(m.get("price"), int):
                    apc_usd = m["price"]
                    break
        lics = bib.get("license") or []
        oa_lic = lics[0].get("type") if lics else None
        subjects = [s.get("term") for s in (bib.get("subject") or []) if s.get("term")]
        ref = bib.get("ref") or {}
        journals.append(
            JournalRecord(
                id=f"doaj:{r.get('id', '')}",
                title=bib.get("title") or "Unknown DOAJ Journal",
                issn_l=issns[0] if issns else None,
                issns=issns,
                publisher=(bib.get("publisher") or {}).get("name"),
                country_code=(bib.get("publisher") or {}).get("country"),
                is_oa=True,
                is_in_doaj=True,
                apc_usd=apc_usd,
                oa_license=oa_lic,
                homepage_url=ref.get("journal"),
                topics=subjects,
                source_providers=["doaj"],
            )
        )
    return journals


async def search_articles_doaj(
    client: httpx.AsyncClient,
    query: str,
    limit: int = 10,
) -> List[PaperRecord]:
    encoded_q = query.replace("/", "%5C/")
    url = f"{DOAJ_BASE}/search/articles/{encoded_q}"
    resp = await client.get(url, params={"pageSize": min(max(limit, 1), 50)}, timeout=12.0)
    if resp.status_code != 200:
        return []
    results = resp.json().get("results") or []
    papers: List[PaperRecord] = []
    for r in results[:limit]:
        bib = r.get("bibjson") or {}
        doi: Optional[str] = None
        issns: List[str] = []
        for ident in bib.get("identifier") or []:
            if ident.get("type") == "doi":
                doi = clean_doi(ident.get("id"))
            elif ident.get("type") in ("pissn", "eissn") and ident.get("id"):
                issns.append(ident["id"])
        pdf_url: Optional[str] = None
        landing_url: Optional[str] = None
        for lnk in bib.get("link") or []:
            if lnk.get("type") == "fulltext" and lnk.get("url"):
                if "pdf" in (lnk.get("content_type") or "").lower() or lnk["url"].endswith(".pdf"):
                    pdf_url = lnk["url"]
                else:
                    landing_url = lnk["url"]
        authors = [
            AuthorRecord(name=a.get("name"), affiliations=[a["affiliation"]] if a.get("affiliation") else [])
            for a in (bib.get("author") or [])
            if a.get("name")
        ]
        j_obj = bib.get("journal") or {}
        journal = JournalSummary(
            name=j_obj.get("title"),
            issn_l=issns[0] if issns else None,
            issns=issns,
            publisher=j_obj.get("publisher"),
            is_oa=True,
            is_in_doaj=True,
        )
        year_str = str(bib.get("year") or "")
        year = int(year_str) if year_str.isdigit() else None
        papers.append(
            PaperRecord(
                id=f"doaj:{r.get('id', '')}",
                title=bib.get("title") or "Untitled",
                doi=doi,
                authors=authors,
                year=year,
                publication_type="journal-article",
                journal=journal,
                volume=j_obj.get("volume"),
                issue=j_obj.get("number"),
                pages=f"{bib.get('start_page', '')}-{bib.get('end_page', '')}".strip("-") or None,
                abstract=bib.get("abstract"),
                is_oa=True,
                oa_status="gold",
                pdf_url=pdf_url,
                landing_page_url=landing_url or pdf_url,
                fields_of_study=[s.get("term") for s in (bib.get("subject") or []) if s.get("term")],
                source_providers=["doaj"],
            )
        )
    return papers


async def search_papers_dblp(
    client: httpx.AsyncClient,
    query: str,
    limit: int = 10,
) -> List[PaperRecord]:
    resp = await _dblp_get_with_anubis(
        client,
        f"{DBLP_BASE}/publ/api",
        params={"q": query, "format": "json", "h": min(max(limit, 1), 100)},
    )
    if resp.status_code != 200 or not resp.text.strip().startswith("{"):
        return []
    hits = (((resp.json().get("result") or {}).get("hits") or {}).get("hit")) or []
    papers: List[PaperRecord] = []
    for h in hits[:limit]:
        info = h.get("info") or {}
        key = info.get("key")
        doi = clean_doi(info.get("doi"))
        raw_authors = (info.get("authors") or {}).get("author") or []
        if isinstance(raw_authors, dict):
            raw_authors = [raw_authors]
        authors: List[AuthorRecord] = []
        for a in raw_authors:
            name = a.get("text") if isinstance(a, dict) else str(a)
            if name:
                clean_name = re.sub(r"\s+\d{4}$", "", name).strip()
                authors.append(AuthorRecord(name=clean_name))
        year_str = str(info.get("year") or "")
        year = int(year_str) if year_str.isdigit() else None
        venue = info.get("venue")
        if isinstance(venue, list):
            venue = venue[0]
        journal = JournalSummary(name=venue) if venue else None
        ee = info.get("ee")
        if isinstance(ee, list):
            ee = ee[0]
        arxiv_id = clean_arxiv_id(ee) if ee and "arxiv.org" in ee else None
        papers.append(
            PaperRecord(
                id=f"dblp:{key}" if key else "dblp:unknown",
                title=(info.get("title") or "Untitled").rstrip("."),
                doi=doi,
                arxiv_id=arxiv_id,
                dblp_key=key,
                authors=authors,
                year=year,
                publication_type=info.get("type"),
                journal=journal,
                volume=info.get("volume"),
                issue=info.get("number"),
                pages=info.get("pages"),
                is_oa=info.get("access") == "open",
                landing_page_url=ee or info.get("url"),
                source_providers=["dblp"],
            )
        )
    return papers


async def search_venues_dblp(
    client: httpx.AsyncClient,
    query: str,
    limit: int = 10,
) -> List[JournalRecord]:
    resp = await _dblp_get_with_anubis(
        client,
        f"{DBLP_BASE}/venue/api",
        params={"q": query, "format": "json", "h": min(max(limit, 1), 50)},
    )
    if resp.status_code != 200 or not resp.text.strip().startswith("{"):
        return []
    hits = (((resp.json().get("result") or {}).get("hits") or {}).get("hit")) or []
    venues: List[JournalRecord] = []
    for h in hits[:limit]:
        info = h.get("info") or {}
        venues.append(
            JournalRecord(
                id=f"dblp:{info.get('acronym') or info.get('venue', 'venue')}",
                title=info.get("venue") or "Unknown Venue",
                type=(info.get("type") or "venue").lower(),
                homepage_url=info.get("url"),
                source_providers=["dblp"],
            )
        )
    return venues


async def fetch_dblp_bibtex(client: httpx.AsyncClient, dblp_key: str) -> Optional[str]:
    resp = await _dblp_get_with_anubis(
        client,
        f"https://dblp.org/rec/{dblp_key.strip()}.bib",
        params={"param": "0"},
    )
    if resp.status_code == 200 and "@" in resp.text:
        return resp.text.strip()
    return None


async def search_papers_inspire(
    client: httpx.AsyncClient,
    query: str,
    limit: int = 10,
) -> List[PaperRecord]:
    resp = await client.get(
        f"{INSPIRE_BASE}/literature",
        params={"q": query, "size": min(max(limit, 1), 50), "sort": "mostrecent"},
        timeout=12.0,
    )
    if resp.status_code != 200:
        return []
    hits = ((resp.json().get("hits") or {}).get("hits")) or []
    papers: List[PaperRecord] = []
    for h in hits[:limit]:
        recid = str(h.get("id") or "")
        meta = h.get("metadata") or {}
        titles = meta.get("titles") or []
        title = titles[0].get("title") if titles else "Untitled"
        dois = meta.get("dois") or []
        doi = clean_doi(dois[0].get("value")) if dois else None
        eprints = meta.get("arxiv_eprints") or []
        arxiv_id = clean_arxiv_id(eprints[0].get("value")) if eprints else None
        abstracts = meta.get("abstracts") or []
        abstract = abstracts[0].get("value") if abstracts else None
        authors = [
            AuthorRecord(name=a.get("full_name"))
            for a in (meta.get("authors") or [])[:25]
            if a.get("full_name")
        ]
        pub_infos = meta.get("publication_info") or []
        pinfo = pub_infos[0] if pub_infos else {}
        j_title = pinfo.get("journal_title")
        year = pinfo.get("year")
        if not year and meta.get("preprint_date"):
            y_str = str(meta["preprint_date"])[:4]
            if y_str.isdigit():
                year = int(y_str)
        papers.append(
            PaperRecord(
                id=f"inspire:{recid}",
                title=title,
                doi=doi,
                arxiv_id=arxiv_id,
                inspire_id=recid,
                authors=authors,
                year=year,
                publication_date=meta.get("preprint_date"),
                journal=JournalSummary(name=j_title) if j_title else None,
                volume=pinfo.get("journal_volume"),
                issue=pinfo.get("journal_issue"),
                pages=pinfo.get("page_start"),
                abstract=abstract,
                citation_count=meta.get("citation_count"),
                is_oa=bool(arxiv_id),
                pdf_url=f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else None,
                landing_page_url=f"https://inspirehep.net/literature/{recid}",
                source_providers=["inspire_hep"],
            )
        )
    return papers


async def fetch_inspire_bibtex(client: httpx.AsyncClient, inspire_id: str) -> Optional[str]:
    resp = await client.get(
        f"{INSPIRE_BASE}/literature/{inspire_id}",
        params={"format": "bibtex"},
        timeout=10.0,
    )
    if resp.status_code == 200 and "@" in resp.text:
        return resp.text.strip()
    return None


async def resolve_unpaywall_oa(
    client: httpx.AsyncClient,
    doi: str,
    email: str = "research-agent@example.org",
) -> Dict[str, Any]:
    cleaned = clean_doi(doi)
    if not cleaned:
        return {}
    resp = await client.get(
        f"{UNPAYWALL_BASE}/{cleaned}",
        params={"email": email},
        timeout=10.0,
    )
    if resp.status_code != 200:
        return {}
    data = resp.json()
    best = data.get("best_oa_location") or {}
    return {
        "is_oa": data.get("is_oa"),
        "oa_status": data.get("oa_status"),
        "pdf_url": best.get("url_for_pdf") or best.get("url"),
        "landing_page_url": best.get("url_for_landing_page"),
        "license": best.get("license"),
        "version": best.get("version"),
    }


async def get_opencitations(
    client: httpx.AsyncClient,
    doi: str,
    direction: str = "both",
    limit: int = 15,
) -> Dict[str, List[CitationEdge]]:
    cleaned = clean_doi(doi)
    if not cleaned:
        return {"citing": [], "references": []}

    citing_edges: List[CitationEdge] = []
    ref_edges: List[CitationEdge] = []

    if direction in ("both", "citing"):
        resp = await client.get(f"{OPENCITATIONS_BASE}/citations/doi:{cleaned}", timeout=12.0)
        if resp.status_code == 200 and isinstance(resp.json(), list):
            for row in resp.json()[:limit]:
                citing_str = row.get("citing") or ""
                c_doi = clean_doi(citing_str)
                citing_edges.append(
                    CitationEdge(
                        oci=row.get("oci"),
                        direction="citing",
                        paper=PaperRecord(
                            id=f"doi:{c_doi}" if c_doi else citing_str,
                            title=f"Citing work ({c_doi or citing_str})",
                            doi=c_doi,
                            publication_date=row.get("creation"),
                            source_providers=["opencitations"],
                        ),
                        creation_date=row.get("creation"),
                        timespan=row.get("timespan"),
                    )
                )

    if direction in ("both", "references"):
        resp = await client.get(f"{OPENCITATIONS_BASE}/references/doi:{cleaned}", timeout=12.0)
        if resp.status_code == 200 and isinstance(resp.json(), list):
            for row in resp.json()[:limit]:
                cited_str = row.get("cited") or ""
                r_doi = clean_doi(cited_str)
                ref_edges.append(
                    CitationEdge(
                        oci=row.get("oci"),
                        direction="reference",
                        paper=PaperRecord(
                            id=f"doi:{r_doi}" if r_doi else cited_str,
                            title=f"Referenced work ({r_doi or cited_str})",
                            doi=r_doi,
                            publication_date=row.get("creation"),
                            source_providers=["opencitations"],
                        ),
                        creation_date=row.get("creation"),
                        timespan=row.get("timespan"),
                    )
                )

    return {"citing": citing_edges, "references": ref_edges}


async def extract_pdf_text_context(
    client: httpx.AsyncClient,
    pdf_url: str,
    focus_query: Optional[str] = None,
    max_chars: int = 12000,
) -> Tuple[List[Dict[str, str]], List[ContextSnippet], Optional[str]]:
    """Downloads an Open Access PDF (up to 25 MB) and extracts page-level text & focused passages."""
    try:
        resp = await client.get(
            pdf_url,
            follow_redirects=True,
            headers={"User-Agent": "AcadSearchAgent/1.0 (mailto:research-agent@example.org)"},
            timeout=18.0,
        )
        if resp.status_code != 200 or len(resp.content) > 25 * 1024 * 1024:
            return ([], [], None)
        if not resp.content.startswith(b"%PDF"):
            return ([], [], None)
        reader = PdfReader(io.BytesIO(resp.content))
    except Exception:
        return ([], [], None)

    sections: List[Dict[str, str]] = []
    snippets: List[ContextSnippet] = []
    query_terms = [t.lower() for t in re.findall(r"[a-zA-Z0-9]{3,}", focus_query or "")]

    max_pages = min(len(reader.pages), 25)
    for page_idx in range(max_pages):
        try:
            raw_text = reader.pages[page_idx].extract_text() or ""
            clean_text = re.sub(r"\s+", " ", raw_text).strip()
            if len(clean_text) < 40:
                continue
            sec_label = f"PDF Page {page_idx + 1}"
            sections.append({"heading": sec_label, "content": clean_text[:2000]})
            if query_terms:
                hits = sum(1 for qt in query_terms if qt in clean_text.lower())
                if hits > 0:
                    snippets.append(
                        ContextSnippet(
                            section=sec_label,
                            text=clean_text[:1200],
                            source="open_access_pdf_pypdf",
                            score=float(hits) / len(query_terms),
                        )
                    )
        except Exception:
            continue

    snippets.sort(key=lambda s: s.score or 0.0, reverse=True)
    if not snippets and sections:
        for s in sections[:4]:
            snippets.append(
                ContextSnippet(
                    section=s["heading"],
                    text=s["content"][:1000],
                    source="open_access_pdf_pypdf",
                )
            )
    full_excerpt = "\n\n".join(f"### {s['heading']}\n{s['content']}" for s in sections)[:max_chars]
    return (sections[:10], snippets[:8], full_excerpt or None)
