from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple
import httpx
from bs4 import BeautifulSoup
from ..models import AuthorRecord, ContextSnippet, JournalSummary, PaperRecord
from ..utils import clean_arxiv_id, clean_doi

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


def _parse_arxiv_entry(entry: ET.Element) -> PaperRecord:
    raw_id = (entry.findtext(f"{ATOM_NS}id") or "").strip()
    arxiv_id = clean_arxiv_id(raw_id) or raw_id
    title = re.sub(r"\s+", " ", (entry.findtext(f"{ATOM_NS}title") or "").strip())
    summary = re.sub(r"\s+", " ", (entry.findtext(f"{ATOM_NS}summary") or "").strip())
    published = (entry.findtext(f"{ATOM_NS}published") or "").strip()
    year = int(published[:4]) if len(published) >= 4 and published[:4].isdigit() else None
    pub_date = published[:10] if len(published) >= 10 else published

    authors: List[AuthorRecord] = []
    for a_el in entry.findall(f"{ATOM_NS}author"):
        name = (a_el.findtext(f"{ATOM_NS}name") or "").strip()
        if not name:
            continue
        affs = [
            (af.text or "").strip()
            for af in a_el.findall(f"{ARXIV_NS}affiliation")
            if (af.text or "").strip()
        ]
        authors.append(AuthorRecord(name=name, affiliations=affs))

    doi = clean_doi(entry.findtext(f"{ARXIV_NS}doi"))
    journal_ref = (entry.findtext(f"{ARXIV_NS}journal_ref") or "").strip()
    journal = JournalSummary(name=journal_ref, is_oa=True) if journal_ref else JournalSummary(name="arXiv", is_oa=True)

    categories: List[str] = []
    for cat in entry.findall(f"{ATOM_NS}category"):
        term = cat.attrib.get("term")
        if term:
            categories.append(term)

    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else None
    html_url = f"https://arxiv.org/html/{arxiv_id}" if arxiv_id else None

    return PaperRecord(
        id=f"arxiv:{arxiv_id}",
        title=title or "Untitled",
        doi=doi,
        arxiv_id=arxiv_id,
        authors=authors,
        year=year,
        publication_date=pub_date,
        publication_type="preprint",
        journal=journal,
        abstract=summary,
        is_oa=True,
        oa_status="green",
        pdf_url=pdf_url,
        html_url=html_url,
        landing_page_url=f"https://arxiv.org/abs/{arxiv_id}",
        fields_of_study=categories,
        source_providers=["arxiv"],
    )


async def search_arxiv(
    client: httpx.AsyncClient,
    query: str,
    limit: int = 10,
    sort_by: str = "relevance",
) -> List[PaperRecord]:
    if any(p in query for p in ("ti:", "au:", "abs:", "cat:", "all:")):
        search_q = query
    else:
        clean_q = query.replace('"', "").strip()
        words = [w for w in re.findall(r"[A-Za-z0-9\-]+", clean_q) if len(w) > 1]
        if len(words) >= 2:
            and_clause = " AND ".join(f"all:{w}" for w in words[:8])
            search_q = f'ti:"{clean_q}" OR abs:"{clean_q}" OR ({and_clause})'
        else:
            search_q = f"all:{clean_q}"
    params = {
        "search_query": search_q,
        "start": 0,
        "max_results": min(max(limit, 1), 100),
        "sortBy": sort_by,
        "sortOrder": "descending",
    }
    resp = await client.get(ARXIV_API_URL, params=params, follow_redirects=True, timeout=15.0)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    entries = root.findall(f"{ATOM_NS}entry")
    papers: List[PaperRecord] = []
    for entry in entries:
        if (entry.findtext(f"{ATOM_NS}title") or "").strip() == "Error":
            continue
        papers.append(_parse_arxiv_entry(entry))
    return papers[:limit]


async def get_arxiv_paper(client: httpx.AsyncClient, arxiv_id: str) -> Optional[PaperRecord]:
    cleaned = clean_arxiv_id(arxiv_id)
    if not cleaned:
        return None
    resp = await client.get(
        ARXIV_API_URL,
        params={"id_list": cleaned, "max_results": 1},
        follow_redirects=True,
        timeout=12.0,
    )
    if resp.status_code != 200:
        return None
    root = ET.fromstring(resp.text)
    entries = root.findall(f"{ATOM_NS}entry")
    if not entries:
        return None
    return _parse_arxiv_entry(entries[0])


async def fetch_arxiv_bibtex(client: httpx.AsyncClient, arxiv_id: str) -> Optional[str]:
    cleaned = clean_arxiv_id(arxiv_id)
    if not cleaned:
        return None
    resp = await client.get(f"https://arxiv.org/bibtex/{cleaned}", follow_redirects=True, timeout=10.0)
    if resp.status_code == 200 and "@" in resp.text:
        return resp.text.strip()
    return None


async def extract_arxiv_html_context(
    client: httpx.AsyncClient,
    arxiv_id: str,
    focus_query: Optional[str] = None,
    max_chars: int = 12000,
) -> Tuple[List[Dict[str, str]], List[ContextSnippet], Optional[str]]:
    """
    Cascades through native arXiv LaTeXML HTML (https://arxiv.org/html/{id})
    and ar5iv (https://ar5iv.labs.arxiv.org/html/{id}) to extract structured sections and equations.
    """
    cleaned = clean_arxiv_id(arxiv_id)
    if not cleaned:
        return ([], [], None)

    urls = [
        f"https://arxiv.org/html/{cleaned}",
        f"https://ar5iv.labs.arxiv.org/html/{cleaned}",
    ]
    html_text: Optional[str] = None
    used_source = "arxiv_html"
    for idx, url in enumerate(urls):
        try:
            resp = await client.get(url, follow_redirects=True, timeout=12.0)
            if resp.status_code == 200 and "<article" in resp.text.lower():
                html_text = resp.text
                used_source = "arxiv_html" if idx == 0 else "ar5iv_html"
                break
        except Exception:
            continue

    if not html_text:
        return ([], [], None)

    soup = BeautifulSoup(html_text, "lxml")
    sections: List[Dict[str, str]] = []
    snippets: List[ContextSnippet] = []
    query_terms = [t.lower() for t in re.findall(r"[a-zA-Z0-9]{3,}", focus_query or "")]

    for sec in soup.find_all(["section"], class_=re.compile(r"ltx_section|ltx_subsection")):
        h_tag = sec.find(["h1", "h2", "h3", "h4"])
        sec_title = re.sub(r"\s+", " ", h_tag.get_text(" ", strip=True)) if h_tag else "Section"
        paras = [re.sub(r"\s+", " ", p.get_text(" ", strip=True)) for p in sec.find_all("p", recursive=False)]
        if not paras:
            paras = [re.sub(r"\s+", " ", p.get_text(" ", strip=True)) for p in sec.find_all("p")[:6]]
        body = "\n".join(p for p in paras if len(p) > 30)
        if not body:
            continue
        sections.append({"heading": sec_title, "content": body[:2000]})
        if query_terms:
            lower_body = (sec_title + " " + body).lower()
            hits = sum(1 for qt in query_terms if qt in lower_body)
            if hits > 0:
                snippets.append(
                    ContextSnippet(
                        section=sec_title,
                        text=body[:1200],
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
    return (sections[:12], snippets[:8], full_excerpt or None)
