from __future__ import annotations
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple
from .models import JournalMetrics, JournalRecord, JournalSummary, PaperRecord

DOI_REGEX = re.compile(r"(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)", re.IGNORECASE)
ARXIV_REGEX = re.compile(
    r"^(?:arxiv:)?(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)$",
    re.IGNORECASE,
)
ISSN_REGEX = re.compile(r"^(\d{4}-\d{3}[\dX])$", re.IGNORECASE)
PMID_REGEX = re.compile(r"^(?:pmid:)?(\d{5,9})$", re.IGNORECASE)
PMCID_REGEX = re.compile(r"^(?:pmcid?:?)?(PMC\d{5,9})$", re.IGNORECASE)
OPENALEX_WORK_REGEX = re.compile(r"^(?:https?://openalex\.org/)?(W\d{6,15})$", re.IGNORECASE)
OPENALEX_SOURCE_REGEX = re.compile(r"^(?:https?://openalex\.org/)?(S\d{6,15})$", re.IGNORECASE)


def clean_doi(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    val = raw.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "doi:", "DOI:"):
        if val.startswith(prefix):
            val = val[len(prefix):].strip()
    m = DOI_REGEX.search(val)
    return m.group(1).lower().rstrip(".") if m else None


def clean_arxiv_id(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    val = raw.strip()
    for prefix in (
        "https://arxiv.org/abs/",
        "http://arxiv.org/abs/",
        "https://arxiv.org/pdf/",
        "https://arxiv.org/html/",
        "arxiv:",
        "arXiv:",
    ):
        if val.startswith(prefix):
            val = val[len(prefix):].strip()
    if val.endswith(".pdf"):
        val = val[:-4]
    val = re.sub(r"v\d+$", "", val)
    m = ARXIV_REGEX.match(val)
    return m.group(1) if m else None


def classify_identifier(identifier: str) -> Tuple[str, str]:
    """
    Returns (id_type, normalized_value) where id_type is one of:
    'doi', 'arxiv', 'pmcid', 'pmid', 'openalex_work', 'openalex_source', 'issn', 'dblp', 'query'
    """
    s = identifier.strip()
    doi = clean_doi(s)
    if doi and (s.lower().startswith("10.") or "doi.org/" in s.lower() or s.lower().startswith("doi:")):
        return ("doi", doi)
    arxiv = clean_arxiv_id(s)
    if arxiv:
        return ("arxiv", arxiv)
    m_pmc = PMCID_REGEX.match(s)
    if m_pmc:
        return ("pmcid", m_pmc.group(1).upper())
    m_oa_w = OPENALEX_WORK_REGEX.match(s)
    if m_oa_w:
        return ("openalex_work", m_oa_w.group(1).upper())
    m_oa_s = OPENALEX_SOURCE_REGEX.match(s)
    if m_oa_s:
        return ("openalex_source", m_oa_s.group(1).upper())
    m_issn = ISSN_REGEX.match(s)
    if m_issn:
        return ("issn", m_issn.group(1).upper())
    m_pmid = PMID_REGEX.match(s)
    if m_pmid:
        return ("pmid", m_pmid.group(1))
    if s.startswith("journals/") or s.startswith("conf/") or s.startswith("series/"):
        return ("dblp", s.strip())
    if doi:
        return ("doi", doi)
    return ("query", s)


def reconstruct_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> Optional[str]:
    """Reconstructs plaintext abstract from OpenAlex abstract_inverted_index."""
    if not inverted_index or not isinstance(inverted_index, dict):
        return None
    max_pos = -1
    for positions in inverted_index.values():
        if positions:
            local_max = max(positions)
            if local_max > max_pos:
                max_pos = local_max
    if max_pos < 0 or max_pos > 50000:
        return None
    words = [""] * (max_pos + 1)
    for token, positions in inverted_index.items():
        for pos in positions:
            if 0 <= pos <= max_pos:
                words[pos] = token
    text = " ".join(w for w in words if w).strip()
    return text if text else None


def normalize_title_key(title: str) -> str:
    if not title:
        return ""
    norm = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    norm = re.sub(r"[^a-z0-9]+", "", norm.lower())
    return norm[:120]


def make_bibtex_citation_key(paper: PaperRecord) -> str:
    first_author = "anon"
    if paper.authors:
        parts = paper.authors[0].name.strip().split()
        if parts:
            surname = parts[-1] if "," not in paper.authors[0].name else paper.authors[0].name.split(",")[0]
            first_author = re.sub(r"[^a-zA-Z0-9]", "", surname).lower() or "author"
    year_str = str(paper.year or "nd")
    stop = {"the", "a", "an", "of", "in", "on", "for", "and", "to", "with", "by", "from", "towards", "using"}
    title_words = re.findall(r"[a-zA-Z0-9]+", (paper.title or "").lower())
    first_word = next((w for w in title_words if w not in stop and len(w) > 2), "paper")
    return f"{first_author}{year_str}{first_word}"


def synthesize_bibtex(paper: PaperRecord) -> str:
    """Synthesizes clean, standard BibTeX from a PaperRecord."""
    if paper.bibtex and "@" in paper.bibtex:
        return paper.bibtex.strip()
    cite_key = make_bibtex_citation_key(paper)
    pub_type = (paper.publication_type or "").lower()
    entry_type = "article"
    if "conf" in pub_type or "proceedings" in pub_type or (paper.dblp_key and paper.dblp_key.startswith("conf/")):
        entry_type = "inproceedings"
    elif "book" in pub_type:
        entry_type = "book"
    elif paper.arxiv_id and not (paper.journal and paper.journal.name):
        entry_type = "misc"

    fields: List[Tuple[str, str]] = []
    if paper.authors:
        authors_str = " and ".join(a.name for a in paper.authors if a.name)
        fields.append(("author", authors_str))
    if paper.title:
        fields.append(("title", "{" + paper.title.replace("{", "").replace("}", "") + "}"))
    if paper.journal and paper.journal.name:
        venue_field = "booktitle" if entry_type == "inproceedings" else "journal"
        fields.append((venue_field, paper.journal.name))
    if paper.year:
        fields.append(("year", str(paper.year)))
    if paper.volume:
        fields.append(("volume", str(paper.volume)))
    if paper.issue:
        fields.append(("number", str(paper.issue)))
    if paper.pages:
        fields.append(("pages", str(paper.pages)))
    if paper.journal and paper.journal.publisher:
        fields.append(("publisher", paper.journal.publisher))
    if paper.doi:
        fields.append(("doi", paper.doi))
        fields.append(("url", f"https://doi.org/{paper.doi}"))
    elif paper.landing_page_url or paper.pdf_url:
        fields.append(("url", paper.landing_page_url or paper.pdf_url or ""))
    if paper.arxiv_id:
        fields.append(("eprint", paper.arxiv_id))
        fields.append(("archivePrefix", "arXiv"))

    lines = [f"@{entry_type}{{{cite_key},"]
    for idx, (k, v) in enumerate(fields):
        comma = "," if idx < len(fields) - 1 else ""
        lines.append(f"  {k} = {{{v}}}{comma}")
    lines.append("}")
    return "\n".join(lines)


def merge_two_papers(primary: PaperRecord, secondary: PaperRecord) -> PaperRecord:
    """Merges two PaperRecords referring to the same work, preserving the richest fields."""
    p = primary.model_copy(deep=True)
    p.doi = p.doi or secondary.doi
    p.arxiv_id = p.arxiv_id or secondary.arxiv_id
    p.pmid = p.pmid or secondary.pmid
    p.pmcid = p.pmcid or secondary.pmcid
    p.openalex_id = p.openalex_id or secondary.openalex_id
    p.semantic_scholar_id = p.semantic_scholar_id or secondary.semantic_scholar_id
    p.dblp_key = p.dblp_key or secondary.dblp_key
    p.inspire_id = p.inspire_id or secondary.inspire_id
    if not p.authors or (len(secondary.authors) > len(p.authors)):
        p.authors = secondary.authors
    else:
        for i, a in enumerate(p.authors):
            if not a.orcid and i < len(secondary.authors) and secondary.authors[i].orcid:
                a.orcid = secondary.authors[i].orcid
    p.year = p.year or secondary.year
    p.publication_date = p.publication_date or secondary.publication_date
    p.publication_type = p.publication_type or secondary.publication_type
    if not p.journal and secondary.journal:
        p.journal = secondary.journal
    elif p.journal and secondary.journal:
        p.journal.name = p.journal.name or secondary.journal.name
        p.journal.issn_l = p.journal.issn_l or secondary.journal.issn_l
        p.journal.publisher = p.journal.publisher or secondary.journal.publisher
        if p.journal.is_oa is None:
            p.journal.is_oa = secondary.journal.is_oa
        if p.journal.is_in_doaj is None:
            p.journal.is_in_doaj = secondary.journal.is_in_doaj
        if not p.journal.metrics and secondary.journal.metrics:
            p.journal.metrics = secondary.journal.metrics
        for issn in secondary.journal.issns:
            if issn not in p.journal.issns:
                p.journal.issns.append(issn)
    p.volume = p.volume or secondary.volume
    p.issue = p.issue or secondary.issue
    p.pages = p.pages or secondary.pages
    if not p.abstract or (secondary.abstract and len(secondary.abstract) > len(p.abstract)):
        p.abstract = secondary.abstract
    p.tldr = p.tldr or secondary.tldr
    if secondary.citation_count is not None:
        if p.citation_count is None or secondary.citation_count > p.citation_count:
            p.citation_count = secondary.citation_count
    p.influential_citation_count = (
        p.influential_citation_count
        if p.influential_citation_count is not None
        else secondary.influential_citation_count
    )
    p.reference_count = p.reference_count if p.reference_count is not None else secondary.reference_count
    p.is_oa = p.is_oa if p.is_oa is not None else secondary.is_oa
    p.oa_status = p.oa_status or secondary.oa_status
    p.pdf_url = p.pdf_url or secondary.pdf_url
    p.html_url = p.html_url or secondary.html_url
    p.landing_page_url = p.landing_page_url or secondary.landing_page_url
    p.bibtex = p.bibtex or secondary.bibtex
    for snip in secondary.pdf_context_snippets:
        if snip.text not in {s.text for s in p.pdf_context_snippets}:
            p.pdf_context_snippets.append(snip)
    for fos in secondary.fields_of_study:
        if fos not in p.fields_of_study:
            p.fields_of_study.append(fos)
    p.is_retracted = p.is_retracted or secondary.is_retracted
    for prov in secondary.source_providers:
        if prov not in p.source_providers:
            p.source_providers.append(prov)
    return p


def deduplicate_and_merge_papers(papers: List[PaperRecord]) -> List[PaperRecord]:
    merged: List[PaperRecord] = []
    doi_index: Dict[str, int] = {}
    arxiv_index: Dict[str, int] = {}
    title_index: Dict[str, int] = {}

    for paper in papers:
        doi = clean_doi(paper.doi)
        paper.doi = doi
        arxiv = clean_arxiv_id(paper.arxiv_id)
        paper.arxiv_id = arxiv
        tkey = normalize_title_key(paper.title)

        match_idx: Optional[int] = None
        if doi and doi in doi_index:
            match_idx = doi_index[doi]
        elif arxiv and arxiv in arxiv_index:
            match_idx = arxiv_index[arxiv]
        elif tkey and len(tkey) >= 16 and tkey in title_index:
            match_idx = title_index[tkey]

        if match_idx is not None:
            merged[match_idx] = merge_two_papers(merged[match_idx], paper)
            m = merged[match_idx]
            if m.doi:
                doi_index[m.doi] = match_idx
            if m.arxiv_id:
                arxiv_index[m.arxiv_id] = match_idx
        else:
            idx = len(merged)
            merged.append(paper)
            if doi:
                doi_index[doi] = idx
            if arxiv:
                arxiv_index[arxiv] = idx
            if tkey and len(tkey) >= 16:
                title_index[tkey] = idx

    return merged


def deduplicate_and_merge_journals(journals: List[JournalRecord]) -> List[JournalRecord]:
    merged: List[JournalRecord] = []
    issn_index: Dict[str, int] = {}
    title_index: Dict[str, int] = {}

    for j in journals:
        all_issns = list(dict.fromkeys(([j.issn_l] if j.issn_l else []) + j.issns))
        j.issns = all_issns
        tkey = normalize_title_key(j.title)

        match_idx: Optional[int] = None
        for issn in all_issns:
            if issn in issn_index:
                match_idx = issn_index[issn]
                break
        if match_idx is None and tkey and tkey in title_index:
            match_idx = title_index[tkey]

        if match_idx is not None:
            cur = merged[match_idx]
            cur.issn_l = cur.issn_l or j.issn_l
            for issn in j.issns:
                if issn not in cur.issns:
                    cur.issns.append(issn)
                    issn_index[issn] = match_idx
            cur.publisher = cur.publisher or j.publisher
            cur.host_organization = cur.host_organization or j.host_organization
            cur.country_code = cur.country_code or j.country_code
            if cur.is_oa is None:
                cur.is_oa = j.is_oa
            if cur.is_in_doaj is None:
                cur.is_in_doaj = j.is_in_doaj
            cur.apc_usd = cur.apc_usd if cur.apc_usd is not None else j.apc_usd
            cur.oa_license = cur.oa_license or j.oa_license
            cur.homepage_url = cur.homepage_url or j.homepage_url
            if j.metrics:
                cur.metrics.two_year_mean_citedness = (
                    cur.metrics.two_year_mean_citedness or j.metrics.two_year_mean_citedness
                )
                cur.metrics.h_index = cur.metrics.h_index or j.metrics.h_index
                cur.metrics.i10_index = cur.metrics.i10_index or j.metrics.i10_index
                cur.metrics.works_count = cur.metrics.works_count or j.metrics.works_count
                cur.metrics.cited_by_count = cur.metrics.cited_by_count or j.metrics.cited_by_count
                cur.metrics.citescore = cur.metrics.citescore or j.metrics.citescore
                cur.metrics.sjr = cur.metrics.sjr or j.metrics.sjr
                cur.metrics.snip = cur.metrics.snip or j.metrics.snip
            for top in j.topics:
                if top not in cur.topics:
                    cur.topics.append(top)
            for prov in j.source_providers:
                if prov not in cur.source_providers:
                    cur.source_providers.append(prov)
        else:
            idx = len(merged)
            merged.append(j)
            for issn in all_issns:
                issn_index[issn] = idx
            if tkey:
                title_index[tkey] = idx

    return merged
