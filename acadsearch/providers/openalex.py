from __future__ import annotations
from typing import Any, Dict, List, Optional
import httpx
from ..models import (
    AuthorRecord,
    CitationEdge,
    JournalMetrics,
    JournalRecord,
    JournalSummary,
    PaperRecord,
)
from ..utils import clean_arxiv_id, clean_doi, reconstruct_abstract

OPENALEX_BASE = "https://api.openalex.org"


def _parse_openalex_work(item: Dict[str, Any]) -> PaperRecord:
    oa_id = (item.get("id") or "").replace("https://openalex.org/", "")
    ids = item.get("ids") or {}
    doi = clean_doi(item.get("doi") or ids.get("doi"))
    pmid_raw = ids.get("pmid") or ""
    pmid = pmid_raw.replace("https://pubmed.ncbi.nlm.nih.gov/", "").strip("/") if pmid_raw else None
    pmcid_raw = ids.get("pmcid") or ""
    pmcid = pmcid_raw.replace("https://www.ncbi.nlm.nih.gov/pmc/articles/", "").strip("/") if pmcid_raw else None

    # Check locations for arXiv ID
    arxiv_id: Optional[str] = None
    for loc in item.get("locations") or []:
        landing = loc.get("landing_page_url") or ""
        if "arxiv.org/abs/" in landing:
            arxiv_id = clean_arxiv_id(landing)
            if arxiv_id:
                break

    authors: List[AuthorRecord] = []
    for auth in item.get("authorships") or []:
        author_obj = auth.get("author") or {}
        name = author_obj.get("display_name") or auth.get("raw_author_name")
        if not name:
            continue
        orcid = (author_obj.get("orcid") or "").replace("https://orcid.org/", "") or None
        a_id = (author_obj.get("id") or "").replace("https://openalex.org/", "") or None
        affs = [inst.get("display_name") for inst in (auth.get("institutions") or []) if inst.get("display_name")]
        authors.append(AuthorRecord(name=name, orcid=orcid, author_id=a_id, affiliations=affs))

    primary_loc = item.get("primary_location") or {}
    source = primary_loc.get("source") or {}
    journal_summary: Optional[JournalSummary] = None
    if source and source.get("display_name"):
        journal_summary = JournalSummary(
            name=source.get("display_name"),
            issn_l=source.get("issn_l"),
            issns=source.get("issn") or [],
            publisher=source.get("host_organization_name"),
            is_oa=source.get("is_oa"),
            is_in_doaj=source.get("is_in_doaj"),
            source_id=(source.get("id") or "").replace("https://openalex.org/", "") or None,
        )

    biblio = item.get("biblio") or {}
    first_page = biblio.get("first_page")
    last_page = biblio.get("last_page")
    pages = f"{first_page}-{last_page}" if first_page and last_page and first_page != last_page else first_page

    oa_info = item.get("open_access") or {}
    best_oa = item.get("best_oa_location") or primary_loc or {}
    pdf_url = best_oa.get("pdf_url") or oa_info.get("oa_url")
    landing_url = primary_loc.get("landing_page_url") or (f"https://doi.org/{doi}" if doi else item.get("id"))

    abstract = reconstruct_abstract(item.get("abstract_inverted_index"))
    topics = [t.get("display_name") for t in (item.get("topics") or [])[:6] if t.get("display_name")]

    return PaperRecord(
        id=f"openalex:{oa_id}" if oa_id else (f"doi:{doi}" if doi else "openalex:unknown"),
        title=item.get("display_name") or item.get("title") or "Untitled",
        doi=doi,
        arxiv_id=arxiv_id,
        pmid=pmid,
        pmcid=pmcid,
        openalex_id=oa_id or None,
        authors=authors,
        year=item.get("publication_year"),
        publication_date=item.get("publication_date"),
        publication_type=item.get("type"),
        journal=journal_summary,
        volume=biblio.get("volume"),
        issue=biblio.get("issue"),
        pages=pages,
        abstract=abstract,
        citation_count=item.get("cited_by_count"),
        reference_count=item.get("referenced_works_count") or len(item.get("referenced_works") or []),
        is_oa=oa_info.get("is_oa"),
        oa_status=oa_info.get("oa_status"),
        pdf_url=pdf_url,
        landing_page_url=landing_url,
        fields_of_study=topics,
        is_retracted=bool(item.get("is_retracted")),
        source_providers=["openalex"],
    )


def _parse_openalex_source(item: Dict[str, Any]) -> JournalRecord:
    src_id = (item.get("id") or "").replace("https://openalex.org/", "")
    stats = item.get("summary_stats") or {}
    metrics = JournalMetrics(
        two_year_mean_citedness=stats.get("2yr_mean_citedness"),
        h_index=stats.get("h_index"),
        i10_index=stats.get("i10_index"),
        works_count=item.get("works_count"),
        cited_by_count=item.get("cited_by_count"),
    )
    topics = [t.get("display_name") for t in (item.get("topics") or [])[:8] if t.get("display_name")]
    return JournalRecord(
        id=f"openalex:{src_id}" if src_id else "openalex:source",
        title=item.get("display_name") or "Unknown Journal",
        issn_l=item.get("issn_l"),
        issns=item.get("issn") or [],
        publisher=item.get("host_organization_name"),
        host_organization=item.get("host_organization_name"),
        country_code=item.get("country_code"),
        type=item.get("type") or "journal",
        is_oa=item.get("is_oa"),
        is_in_doaj=item.get("is_in_doaj"),
        apc_usd=item.get("apc_usd"),
        homepage_url=item.get("homepage_url"),
        metrics=metrics,
        topics=topics,
        counts_by_year=(item.get("counts_by_year") or [])[:5],
        source_providers=["openalex"],
    )


async def search_works_openalex(
    client: httpx.AsyncClient,
    query: str,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    open_access_only: bool = False,
    venue_issn: Optional[str] = None,
    min_citations: Optional[int] = None,
    limit: int = 10,
    sort: Optional[str] = None,
    api_key: Optional[str] = None,
    mailto: str = "research-agent@example.org",
) -> List[PaperRecord]:
    params: Dict[str, Any] = {
        "search": query,
        "per_page": min(max(limit, 1), 100),
        "mailto": mailto,
    }
    if api_key:
        params["api_key"] = api_key

    filters: List[str] = []
    if year_min and year_max:
        filters.append(f"publication_year:{year_min}-{year_max}")
    elif year_min:
        filters.append(f"from_publication_date:{year_min}-01-01")
    elif year_max:
        filters.append(f"to_publication_date:{year_max}-12-31")
    if open_access_only:
        filters.append("is_oa:true")
    if venue_issn:
        filters.append(f"primary_location.source.issn:{venue_issn}")
    if min_citations:
        filters.append(f"cited_by_count:>{min_citations - 1}")
    if filters:
        params["filter"] = ",".join(filters)
    if sort == "citations":
        params["sort"] = "cited_by_count:desc"
    elif sort == "year":
        params["sort"] = "publication_date:desc"

    resp = await client.get(f"{OPENALEX_BASE}/works", params=params, timeout=15.0)
    resp.raise_for_status()
    data = resp.json()
    return [_parse_openalex_work(w) for w in (data.get("results") or [])[:limit]]


async def get_work_openalex(
    client: httpx.AsyncClient,
    identifier: str,
    id_type: str = "doi",
    api_key: Optional[str] = None,
    mailto: str = "research-agent@example.org",
) -> Optional[PaperRecord]:
    params: Dict[str, Any] = {"mailto": mailto}
    if api_key:
        params["api_key"] = api_key

    if id_type == "doi":
        url = f"{OPENALEX_BASE}/works/https://doi.org/{identifier}"
    elif id_type == "arxiv":
        url = f"{OPENALEX_BASE}/works/https://doi.org/10.48550/arXiv.{identifier}"
    elif id_type == "pmid":
        url = f"{OPENALEX_BASE}/works/pmid:{identifier}"
    elif id_type == "pmcid":
        url = f"{OPENALEX_BASE}/works/pmcid:{identifier}"
    elif id_type == "openalex_work":
        url = f"{OPENALEX_BASE}/works/{identifier}"
    else:
        return None

    resp = await client.get(url, params=params, timeout=12.0)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return _parse_openalex_work(resp.json())


async def search_journals_openalex(
    client: httpx.AsyncClient,
    query: Optional[str] = None,
    issn: Optional[str] = None,
    open_access_only: bool = False,
    limit: int = 10,
    api_key: Optional[str] = None,
    mailto: str = "research-agent@example.org",
) -> List[JournalRecord]:
    params: Dict[str, Any] = {"mailto": mailto, "per_page": min(max(limit, 1), 100)}
    if api_key:
        params["api_key"] = api_key

    if issn and not query:
        resp = await client.get(f"{OPENALEX_BASE}/sources/issn:{issn}", params=params, timeout=12.0)
        if resp.status_code == 200:
            return [_parse_openalex_source(resp.json())]

    if query:
        params["search"] = query
    filters: List[str] = []
    if issn:
        filters.append(f"issn:{issn}")
    if open_access_only:
        filters.append("is_oa:true")
    if filters:
        params["filter"] = ",".join(filters)

    resp = await client.get(f"{OPENALEX_BASE}/sources", params=params, timeout=15.0)
    resp.raise_for_status()
    data = resp.json()
    return [_parse_openalex_source(s) for s in (data.get("results") or [])[:limit]]


async def get_citations_openalex(
    client: httpx.AsyncClient,
    openalex_id_or_doi: str,
    direction: str = "both",
    limit: int = 15,
    api_key: Optional[str] = None,
    mailto: str = "research-agent@example.org",
) -> Dict[str, List[CitationEdge]]:
    params: Dict[str, Any] = {"mailto": mailto}
    if api_key:
        params["api_key"] = api_key

    work_url = (
        f"{OPENALEX_BASE}/works/{openalex_id_or_doi}"
        if openalex_id_or_doi.upper().startswith("W")
        else f"{OPENALEX_BASE}/works/https://doi.org/{clean_doi(openalex_id_or_doi) or openalex_id_or_doi}"
    )
    w_resp = await client.get(work_url, params=params, timeout=12.0)
    if w_resp.status_code != 200:
        return {"citing": [], "references": []}
    w_json = w_resp.json()
    oa_id = (w_json.get("id") or "").replace("https://openalex.org/", "")
    ref_ids = [r.replace("https://openalex.org/", "") for r in (w_json.get("referenced_works") or [])[:limit]]

    citing_edges: List[CitationEdge] = []
    ref_edges: List[CitationEdge] = []

    if direction in ("both", "citing") and oa_id:
        c_params = dict(params, filter=f"cites:{oa_id}", per_page=min(limit, 50), sort="cited_by_count:desc")
        c_resp = await client.get(f"{OPENALEX_BASE}/works", params=c_params, timeout=12.0)
        if c_resp.status_code == 200:
            for item in (c_resp.json().get("results") or [])[:limit]:
                paper = _parse_openalex_work(item)
                citing_edges.append(
                    CitationEdge(
                        direction="citing",
                        paper=paper,
                        creation_date=paper.publication_date,
                    )
                )

    if direction in ("both", "references") and ref_ids:
        pipe_ids = "|".join(ref_ids[:40])
        r_params = dict(params, filter=f"openalex_id:{pipe_ids}", per_page=min(limit, 50))
        r_resp = await client.get(f"{OPENALEX_BASE}/works", params=r_params, timeout=12.0)
        if r_resp.status_code == 200:
            for item in (r_resp.json().get("results") or [])[:limit]:
                paper = _parse_openalex_work(item)
                ref_edges.append(
                    CitationEdge(
                        direction="reference",
                        paper=paper,
                        creation_date=paper.publication_date,
                    )
                )

    return {"citing": citing_edges, "references": ref_edges}
