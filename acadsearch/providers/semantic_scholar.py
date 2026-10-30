from __future__ import annotations
from typing import Any, Dict, List, Optional
import httpx
from ..models import AuthorRecord, CitationEdge, ContextSnippet, JournalSummary, PaperRecord
from ..utils import clean_arxiv_id, clean_doi

S2_BASE = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = (
    "paperId,externalIds,url,title,abstract,venue,publicationVenue,year,referenceCount,"
    "citationCount,influentialCitationCount,isOpenAccess,openAccessPdf,fieldsOfStudy,"
    "publicationTypes,publicationDate,journal,citationStyles,authors,tldr"
)


def _headers(api_key: Optional[str]) -> Dict[str, str]:
    h = {"Accept": "application/json"}
    if api_key:
        h["x-api-key"] = api_key
    return h


def _parse_s2_paper(item: Dict[str, Any]) -> PaperRecord:
    s2_id = item.get("paperId") or ""
    ext = item.get("externalIds") or {}
    doi = clean_doi(ext.get("DOI"))
    arxiv_id = clean_arxiv_id(ext.get("ArXiv"))
    pmid = str(ext.get("PubMed")) if ext.get("PubMed") else None
    pmcid = str(ext.get("PubMedCentral")) if ext.get("PubMedCentral") else None
    dblp_key = ext.get("DBLP")

    authors = [
        AuthorRecord(
            name=a.get("name") or "Unknown",
            author_id=str(a.get("authorId")) if a.get("authorId") else None,
        )
        for a in (item.get("authors") or [])
        if a.get("name")
    ]

    j_obj = item.get("journal") or {}
    pub_venue = item.get("publicationVenue") or {}
    venue_name = j_obj.get("name") or pub_venue.get("name") or item.get("venue")
    issn = pub_venue.get("issn")
    journal = (
        JournalSummary(
            name=venue_name,
            issn_l=issn,
            issns=[issn] if issn else [],
        )
        if venue_name
        else None
    )

    oa_pdf = item.get("openAccessPdf") or {}
    pdf_url = oa_pdf.get("url")
    tldr_obj = item.get("tldr") or {}
    tldr_text = tldr_obj.get("text") if isinstance(tldr_obj, dict) else None
    cit_styles = item.get("citationStyles") or {}
    bibtex = cit_styles.get("bibtex") if isinstance(cit_styles, dict) else None
    pub_types = item.get("publicationTypes") or []

    return PaperRecord(
        id=f"s2:{s2_id}" if s2_id else (f"doi:{doi}" if doi else "s2:unknown"),
        title=item.get("title") or "Untitled",
        doi=doi,
        arxiv_id=arxiv_id,
        pmid=pmid,
        pmcid=pmcid,
        semantic_scholar_id=s2_id or None,
        dblp_key=dblp_key,
        authors=authors,
        year=item.get("year"),
        publication_date=item.get("publicationDate"),
        publication_type=pub_types[0] if pub_types else None,
        journal=journal,
        volume=j_obj.get("volume"),
        pages=j_obj.get("pages"),
        abstract=item.get("abstract"),
        tldr=tldr_text,
        citation_count=item.get("citationCount"),
        influential_citation_count=item.get("influentialCitationCount"),
        reference_count=item.get("referenceCount"),
        is_oa=item.get("isOpenAccess"),
        oa_status=oa_pdf.get("status"),
        pdf_url=pdf_url,
        landing_page_url=item.get("url"),
        bibtex=bibtex,
        fields_of_study=item.get("fieldsOfStudy") or [],
        source_providers=["semantic_scholar"],
    )


async def search_papers_s2(
    client: httpx.AsyncClient,
    query: str,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    open_access_only: bool = False,
    venue: Optional[str] = None,
    min_citations: Optional[int] = None,
    limit: int = 10,
    api_key: Optional[str] = None,
) -> List[PaperRecord]:
    params: Dict[str, Any] = {
        "query": query,
        "limit": min(max(limit, 1), 100),
        "fields": S2_FIELDS,
    }
    if year_min and year_max:
        params["year"] = f"{year_min}-{year_max}"
    elif year_min:
        params["year"] = f"{year_min}-"
    elif year_max:
        params["year"] = f"-{year_max}"
    if open_access_only:
        params["openAccessPdf"] = ""
    if venue:
        params["venue"] = venue
    if min_citations:
        params["minCitationCount"] = min_citations

    resp = await client.get(f"{S2_BASE}/paper/search", params=params, headers=_headers(api_key), timeout=12.0)
    if resp.status_code == 429:
        # Fallback to /paper/search/bulk which often has separate pool availability
        bulk_resp = await client.get(
            f"{S2_BASE}/paper/search/bulk",
            params=params,
            headers=_headers(api_key),
            timeout=12.0,
        )
        if bulk_resp.status_code == 200:
            items = (bulk_resp.json().get("data") or [])[:limit]
            return [_parse_s2_paper(it) for it in items]
        return []
    resp.raise_for_status()
    items = (resp.json().get("data") or [])[:limit]
    return [_parse_s2_paper(it) for it in items]


async def get_paper_s2(
    client: httpx.AsyncClient,
    identifier: str,
    id_type: str = "doi",
    api_key: Optional[str] = None,
) -> Optional[PaperRecord]:
    if id_type == "doi":
        s2_id_param = f"DOI:{identifier}"
    elif id_type == "arxiv":
        s2_id_param = f"ARXIV:{identifier}"
    elif id_type == "pmid":
        s2_id_param = f"PMID:{identifier}"
    elif id_type == "pmcid":
        s2_id_param = f"PMCID:{identifier}"
    else:
        s2_id_param = identifier

    resp = await client.get(
        f"{S2_BASE}/paper/{s2_id_param}",
        params={"fields": S2_FIELDS},
        headers=_headers(api_key),
        timeout=12.0,
    )
    if resp.status_code in (404, 429):
        return None
    resp.raise_for_status()
    return _parse_s2_paper(resp.json())


async def search_snippets_s2(
    client: httpx.AsyncClient,
    query: str,
    paper_ids: Optional[List[str]] = None,
    limit: int = 10,
    api_key: Optional[str] = None,
) -> List[ContextSnippet]:
    params: Dict[str, Any] = {
        "query": query,
        "limit": min(max(limit, 1), 50),
    }
    if paper_ids:
        params["paperIds"] = ",".join(paper_ids[:50])

    resp = await client.get(
        f"{S2_BASE}/snippet/search",
        params=params,
        headers=_headers(api_key),
        timeout=12.0,
    )
    if resp.status_code != 200:
        return []
    data = resp.json().get("data") or []
    snippets: List[ContextSnippet] = []
    for item in data:
        snip = item.get("snippet") or {}
        text = snip.get("text")
        if not text:
            continue
        section = snip.get("section") or snip.get("snippetKind")
        paper_info = item.get("paper") or {}
        title_prefix = f"[{paper_info.get('title')}] " if paper_info.get("title") and not paper_ids else ""
        snippets.append(
            ContextSnippet(
                section=section,
                text=f"{title_prefix}{text}",
                source="semantic_scholar_snippet",
                score=item.get("score"),
            )
        )
    return snippets
