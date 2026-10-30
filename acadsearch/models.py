from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AuthorRecord(BaseModel):
    name: str
    orcid: Optional[str] = None
    author_id: Optional[str] = None
    affiliations: List[str] = Field(default_factory=list)


class JournalMetrics(BaseModel):
    two_year_mean_citedness: Optional[float] = Field(
        default=None,
        description="OpenAlex 2-year mean citedness (open equivalent of 2-year Journal Impact Factor)",
    )
    h_index: Optional[int] = None
    i10_index: Optional[int] = None
    works_count: Optional[int] = None
    cited_by_count: Optional[int] = None
    citescore: Optional[float] = Field(default=None, description="Elsevier Scopus CiteScore")
    sjr: Optional[float] = Field(default=None, description="SCImago Journal Rank (SJR)")
    snip: Optional[float] = Field(default=None, description="Source Normalized Impact per Paper (SNIP)")
    jif: Optional[float] = Field(default=None, description="Clarivate Web of Science Journal Impact Factor (JIF)")
    jci: Optional[float] = Field(default=None, description="Clarivate Journal Citation Indicator (JCI)")
    jif_quartile: Optional[str] = Field(default=None, description="JCR Impact Factor Quartile (Q1-Q4)")
    jif_percentile: Optional[float] = Field(default=None, description="JCR Impact Factor Percentile (0-100)")


class JournalSummary(BaseModel):
    name: Optional[str] = None
    issn_l: Optional[str] = None
    issns: List[str] = Field(default_factory=list)
    publisher: Optional[str] = None
    is_oa: Optional[bool] = None
    is_in_doaj: Optional[bool] = None
    source_id: Optional[str] = None
    metrics: Optional[JournalMetrics] = None


class JournalRecord(BaseModel):
    id: str
    title: str
    issn_l: Optional[str] = None
    issns: List[str] = Field(default_factory=list)
    publisher: Optional[str] = None
    host_organization: Optional[str] = None
    country_code: Optional[str] = None
    type: str = "journal"
    is_oa: Optional[bool] = None
    is_in_doaj: Optional[bool] = None
    apc_usd: Optional[int] = None
    oa_license: Optional[str] = None
    homepage_url: Optional[str] = None
    metrics: JournalMetrics = Field(default_factory=JournalMetrics)
    topics: List[str] = Field(default_factory=list)
    counts_by_year: List[Dict[str, Any]] = Field(default_factory=list)
    source_providers: List[str] = Field(default_factory=list)


class ContextSnippet(BaseModel):
    section: Optional[str] = None
    text: str
    source: str
    score: Optional[float] = None


class PaperRecord(BaseModel):
    id: str
    title: str
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    openalex_id: Optional[str] = None
    semantic_scholar_id: Optional[str] = None
    dblp_key: Optional[str] = None
    inspire_id: Optional[str] = None
    authors: List[AuthorRecord] = Field(default_factory=list)
    year: Optional[int] = None
    publication_date: Optional[str] = None
    publication_type: Optional[str] = None
    journal: Optional[JournalSummary] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    abstract: Optional[str] = None
    tldr: Optional[str] = None
    citation_count: Optional[int] = None
    influential_citation_count: Optional[int] = None
    reference_count: Optional[int] = None
    is_oa: Optional[bool] = None
    oa_status: Optional[str] = None
    pdf_url: Optional[str] = None
    html_url: Optional[str] = None
    landing_page_url: Optional[str] = None
    bibtex: Optional[str] = None
    pdf_context_snippets: List[ContextSnippet] = Field(default_factory=list)
    fields_of_study: List[str] = Field(default_factory=list)
    is_retracted: bool = False
    source_providers: List[str] = Field(default_factory=list)


class PaperContextResult(BaseModel):
    identifier: str
    title: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    abstract: Optional[str] = None
    tldr: Optional[str] = None
    pdf_url: Optional[str] = None
    html_url: Optional[str] = None
    bibtex: Optional[str] = None
    sections: List[Dict[str, str]] = Field(default_factory=list)
    snippets: List[ContextSnippet] = Field(default_factory=list)
    full_text_excerpt: Optional[str] = None
    extraction_sources: List[str] = Field(default_factory=list)


class CitationEdge(BaseModel):
    oci: Optional[str] = None
    direction: str = Field(description="'citing' (incoming) or 'reference' (outgoing)")
    paper: PaperRecord
    creation_date: Optional[str] = None
    timespan: Optional[str] = None
    is_influential: Optional[bool] = None
    citation_context: Optional[str] = None


class CitationGraphResult(BaseModel):
    identifier: str
    citation_count: Optional[int] = None
    reference_count: Optional[int] = None
    citing_papers: List[CitationEdge] = Field(default_factory=list)
    references: List[CitationEdge] = Field(default_factory=list)
    source_providers: List[str] = Field(default_factory=list)


class SearchPapersResponse(BaseModel):
    query: str
    total_returned: int
    providers_queried: List[str]
    results: List[PaperRecord]
    warnings: List[str] = Field(default_factory=list)


class SearchJournalsResponse(BaseModel):
    query: str
    total_returned: int
    providers_queried: List[str]
    results: List[JournalRecord]
    warnings: List[str] = Field(default_factory=list)
