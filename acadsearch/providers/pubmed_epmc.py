from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple
import httpx
from ..models import AuthorRecord, ContextSnippet, JournalSummary, PaperRecord
from ..utils import clean_doi

EPMC_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
BIOC_BASE = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json"
PUBTATOR3_BASE = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api"


def _parse_epmc_item(item: Dict[str, Any]) -> PaperRecord:
    pmid = str(item.get("pmid")) if item.get("pmid") else None
    pmcid = item.get("pmcid")
    doi = clean_doi(item.get("doi"))
    title = (item.get("title") or "Untitled").rstrip(".")

    authors: List[AuthorRecord] = []
    author_list = (item.get("authorList") or {}).get("author") or []
    for a in author_list:
        full_name = a.get("fullName") or f"{a.get('firstName', '')} {a.get('lastName', '')}".strip()
        if not full_name:
            continue
        orcid = None
        if isinstance(a.get("authorId"), dict) and a["authorId"].get("type") == "ORCID":
            orcid = a["authorId"].get("value")
        aff_list = []
        if a.get("affiliation"):
            aff_list.append(a["affiliation"])
        authors.append(AuthorRecord(name=full_name, orcid=orcid, affiliations=aff_list))

    journal_info = item.get("journalInfo") or {}
    j_obj = journal_info.get("journal") or {}
    j_title = j_obj.get("title") or item.get("journalTitle")
    issn = j_obj.get("issn") or j_obj.get("essn")
    issns = [i for i in (j_obj.get("issn"), j_obj.get("essn")) if i]
    is_oa = str(item.get("isOpenAccess", "")).upper() == "Y"

    journal = (
        JournalSummary(
            name=j_title,
            issn_l=issn,
            issns=issns,
            is_oa=is_oa,
        )
        if j_title
        else None
    )

    year_val = item.get("pubYear")
    year = int(year_val) if str(year_val).isdigit() else None

    pdf_url: Optional[str] = None
    full_urls = (item.get("fullTextUrlList") or {}).get("fullTextUrl") or []
    for u in full_urls:
        if u.get("documentStyle") == "pdf" and u.get("url"):
            pdf_url = u.get("url")
            break
    if not pdf_url and pmcid and is_oa:
        pdf_url = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf"

    mesh_terms: List[str] = []
    for mh in (item.get("meshHeadingList") or {}).get("meshHeading") or []:
        if mh.get("descriptorName"):
            mesh_terms.append(mh["descriptorName"])

    return PaperRecord(
        id=f"pmid:{pmid}" if pmid else (f"pmcid:{pmcid}" if pmcid else f"doi:{doi}"),
        title=title,
        doi=doi,
        pmid=pmid,
        pmcid=pmcid,
        authors=authors,
        year=year,
        publication_date=item.get("firstPublicationDate"),
        publication_type=item.get("pubType"),
        journal=journal,
        volume=journal_info.get("volume"),
        issue=journal_info.get("issue"),
        pages=item.get("pageInfo"),
        abstract=item.get("abstractText"),
        citation_count=item.get("citedByCount"),
        is_oa=is_oa,
        pdf_url=pdf_url,
        landing_page_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else (f"https://doi.org/{doi}" if doi else None),
        fields_of_study=mesh_terms[:8],
        source_providers=["pubmed_europepmc"],
    )


async def search_europe_pmc(
    client: httpx.AsyncClient,
    query: str,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    open_access_only: bool = False,
    limit: int = 10,
) -> List[PaperRecord]:
    q_parts = [f"({query})"]
    if year_min and year_max:
        q_parts.append(f"(PUB_YEAR:[{year_min} TO {year_max}])")
    elif year_min:
        q_parts.append(f"(PUB_YEAR:[{year_min} TO 2099])")
    elif year_max:
        q_parts.append(f"(PUB_YEAR:[1900 TO {year_max}])")
    if open_access_only:
        q_parts.append("(OPEN_ACCESS:y)")

    params = {
        "query": " AND ".join(q_parts),
        "resultType": "core",
        "format": "json",
        "pageSize": min(max(limit, 1), 100),
    }
    resp = await client.get(f"{EPMC_BASE}/search", params=params, timeout=15.0)
    resp.raise_for_status()
    results = (resp.json().get("resultList") or {}).get("result") or []
    return [_parse_epmc_item(r) for r in results[:limit]]


async def get_paper_europe_pmc(
    client: httpx.AsyncClient,
    identifier: str,
    id_type: str = "pmid",
) -> Optional[PaperRecord]:
    if id_type == "pmid":
        q = f"EXT_ID:{identifier} AND SRC:MED"
    elif id_type == "pmcid":
        q = f"PMCID:{identifier}"
    elif id_type == "doi":
        q = f'DOI:"{identifier}"'
    else:
        q = identifier
    papers = await search_europe_pmc(client, q, limit=1)
    return papers[0] if papers else None


async def extract_pmc_bioc_context(
    client: httpx.AsyncClient,
    pmcid: Optional[str] = None,
    pmid: Optional[str] = None,
    focus_query: Optional[str] = None,
    max_chars: int = 12000,
) -> Tuple[List[Dict[str, str]], List[ContextSnippet], Optional[str]]:
    """
    Fetches structured full-text sections from NCBI PubTator 3.0 BioC JSON API
    (with fallback to NCBI PMC Open Access BioC JSON API).
    """
    passages: List[Dict[str, Any]] = []
    used_source = "ncbi_pubtator3_biocjson"

    # 1. Try NCBI bionlp RESTful BioC_json endpoint first (richest full-text sections)
    for target in [pmcid, pmid]:
        if not target:
            continue
        try:
            resp = await client.get(f"{BIOC_BASE}/{target}/unicode", timeout=12.0)
            if resp.status_code == 200 and resp.text.strip().startswith(("[", "{")):
                data = resp.json()
                docs = (
                    data[0].get("documents")
                    if isinstance(data, list) and data
                    else (data.get("documents") if isinstance(data, dict) else [])
                )
                if docs and docs[0].get("passages"):
                    passages = docs[0]["passages"]
                    used_source = "ncbi_pmc_bioc_json"
                    break
        except Exception:
            pass

    # 2. Fallback to PubTator 3.0 full-text BioC JSON export if PMID is available and passages <= 2
    if len(passages) <= 2 and pmid:
        try:
            pt_resp = await client.get(
                f"{PUBTATOR3_BASE}/publications/export/biocjson",
                params={"pmids": pmid, "full": "true"},
                timeout=12.0,
            )
            if pt_resp.status_code == 200:
                pt_data = pt_resp.json()
                pt_docs = pt_data.get("PubTator3") or []
                if pt_docs and len(pt_docs[0].get("passages") or []) > len(passages):
                    passages = pt_docs[0]["passages"]
                    used_source = "ncbi_pubtator3_biocjson"
        except Exception:
            pass

    if not passages:
        return ([], [], None)

    sec_buckets: Dict[str, List[str]] = {}
    for p in passages:
        infons = p.get("infons") or {}
        sec_type = infons.get("section_type") or infons.get("type") or "BODY"
        text = (p.get("text") or "").strip()
        if len(text) < 25 or sec_type in ("REF", "ACK_FUND", "COMP_INT", "ABBR", "AUTH_CONT"):
            continue
        sec_buckets.setdefault(sec_type, []).append(text)

    sections: List[Dict[str, str]] = []
    snippets: List[ContextSnippet] = []
    query_terms = [t.lower() for t in re.findall(r"[a-zA-Z0-9]{3,}", focus_query or "")]

    for sec_name, texts in sec_buckets.items():
        combined = "\n".join(texts)
        sections.append({"heading": sec_name, "content": combined[:2200]})
        if query_terms:
            hits = sum(1 for qt in query_terms if qt in combined.lower())
            if hits > 0:
                snippets.append(
                    ContextSnippet(
                        section=sec_name,
                        text=combined[:1200],
                        source=used_source,
                        score=float(hits) / len(query_terms),
                    )
                )

    snippets.sort(key=lambda s: s.score or 0.0, reverse=True)
    if not snippets and sections:
        for s in sections[:4]:
            snippets.append(
                ContextSnippet(
                    section=s["heading"],
                    text=s["content"][:1000],
                    source=used_source,
                )
            )
    full_excerpt = "\n\n".join(f"### {s['heading']}\n{s['content']}" for s in sections)[:max_chars]
    return (sections[:10], snippets[:8], full_excerpt or None)
