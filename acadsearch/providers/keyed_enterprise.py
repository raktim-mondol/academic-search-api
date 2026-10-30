from __future__ import annotations
import io
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote
import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
from ..models import (
    AuthorRecord,
    ContextSnippet,
    JournalMetrics,
    JournalRecord,
    JournalSummary,
    PaperRecord,
)
from ..utils import clean_arxiv_id, clean_doi
from .crossref import _parse_crossref_work


PUBLISHER_CROSSREF_MEMBERS: Dict[str, Tuple[int, str]] = {
    "wiley": (311, "Wiley"),
    "elsevier": (78, "Elsevier BV"),
    "scopus": (78, "Elsevier BV"),
    "sciencedirect": (78, "Elsevier BV"),
    "springer": (297, "Springer Science and Business Media LLC"),
    "springer_nature": (297, "Springer Science and Business Media LLC"),
    "nature": (297, "Springer Science and Business Media LLC"),
    "ieee": (263, "Institute of Electrical and Electronics Engineers (IEEE)"),
    "ieee_xplore": (263, "Institute of Electrical and Electronics Engineers (IEEE)"),
    "taylor_francis": (301, "Informa UK Limited (Taylor & Francis)"),
    "sage": (179, "SAGE Publications"),
    "oup": (286, "Oxford University Press (OUP)"),
    "oxford": (286, "Oxford University Press (OUP)"),
    "cup": (56, "Cambridge University Press (CUP)"),
    "cambridge": (56, "Cambridge University Press (CUP)"),
    "acm": (320, "Association for Computing Machinery (ACM)"),
    "acs": (316, "American Chemical Society (ACS)"),
    "aps": (16, "American Physical Society (APS)"),
    "iop": (266, "IOP Publishing"),
    "rsc": (292, "Royal Society of Chemistry (RSC)"),
    "mdpi": (1968, "MDPI AG"),
    "frontiers": (1965, "Frontiers Media SA"),
    "plos": (340, "Public Library of Science (PLoS)"),
}


SUPPORTED_DATABASES_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "openalex",
        "name": "OpenAlex",
        "category": "Open Global Scholarly Graph",
        "corpus_size": "300M+ core works, 250K+ journals/sources",
        "base_url": "https://api.openalex.org",
        "auth": "None required (optional free ?api_key= or mailto= polite pool)",
        "rate_limit": "10 RPS (no key) / 30 RPS (free key) / 50 RPS (annual); singleton ID lookups = $0.00 FREE",
        "capabilities": ["papers", "journals", "metrics", "abstract_inverted_index", "citations", "oa_pdf"],
        "live_without_key": True,
    },
    {
        "id": "semantic_scholar",
        "name": "Semantic Scholar (Ai2)",
        "category": "Open Global Scholarly Graph & Full-Text Snippets",
        "corpus_size": "214M+ papers, 2.49B citations",
        "base_url": "https://api.semanticscholar.org/graph/v1",
        "auth": "None required (optional x-api-key header)",
        "rate_limit": "Shared 1,000 RPS unauthenticated pool; 1 RPS dedicated key",
        "capabilities": ["papers", "bulk_boolean", "snippet_search_500w", "tldr", "bibtex", "specter2_embeddings", "citations"],
        "live_without_key": True,
    },
    {
        "id": "crossref",
        "name": "Crossref & DOI Content Negotiation",
        "category": "Official DOI Registration & Journal Metadata",
        "corpus_size": "180M+ registered DOIs, 100K+ serials",
        "base_url": "https://api.crossref.org/v1",
        "auth": "None required (Polite pool via ?mailto=)",
        "rate_limit": "Polite Pool: 10 RPS single DOI / 3 RPS search; Public: 5 RPS / 1 RPS",
        "capabilities": ["papers", "journals", "doi_resolution", "bibtex_negotiation", "csl_json"],
        "live_without_key": True,
    },
    {
        "id": "elsevier_scopus",
        "name": "Elsevier Scopus, ScienceDirect, Abstract Retrieval & Serial Title API",
        "category": "Commercial Bibliometric, Journal Metrics & Publisher Full-Text",
        "corpus_size": "95M+ Scopus records, 25.5M+ Elsevier DOIs, 29,000+ serial titles (CiteScore/SJR/SNIP)",
        "base_url": "https://api.elsevier.com/content",
        "auth": "X-ELS-APIKey: $ELSEVIER_API_KEY (+ X-ELS-Insttoken); zero-key fallback via Crossref Member 78 + OpenAlex",
        "rate_limit": "2-10 RPS depending on endpoint (20,000/week Scopus Search)",
        "capabilities": ["papers", "scopus_abstract_retrieval", "journal_citescore_sjr_snip", "sciencedirect_fulltext_xml_json"],
        "live_without_key": True,
        "env_var": "ELSEVIER_API_KEY",
    },
    {
        "id": "clarivate_wos",
        "name": "Clarivate Web of Science (Starter v1, Expanded API & JCR Journals v1)",
        "category": "Commercial Citation Index & Journal Impact Factor (JIF)",
        "corpus_size": "90M+ WoS Core Collection records, 21,000+ Journal Citation Reports (JCR) journals",
        "base_url": "https://api.clarivate.com/apis/wos-starter/v1 & https://api.clarivate.com/apis/wos-journals/v1 & https://wos-api.clarivate.com/api/wos",
        "auth": "X-ApiKey: $WOS_API_KEY",
        "rate_limit": "Starter: 1-5 RPS (5,000/day); Expanded: 2-5 RPS (50K-3M Full Records/yr)",
        "capabilities": ["papers", "wos_times_cited", "jcr_impact_factor_jif_jci_quartiles", "cited_references"],
        "live_without_key": False,
        "env_var": "WOS_API_KEY",
    },
    {
        "id": "wiley",
        "name": "Wiley Online Library TDM API v1 & Crossref Member 311",
        "category": "Major Academic Publisher (Journals, Books & Full-Text TDM PDF)",
        "corpus_size": "12.2M+ Wiley Online Library articles & book chapters across 1,600+ journals",
        "base_url": "https://api.wiley.com/onlinelibrary/tdm/v1/articles/{doi} & https://api.crossref.org/v1/members/311/works",
        "auth": "Wiley-TDM-Client-Token: $WILEY_TDM_TOKEN (or $TDM_API_TOKEN) for full-text PDF; zero-key search via Crossref Member 311 + OpenAlex",
        "rate_limit": "Up to 3 requests/second for TDM PDF downloads; 3 RPS Polite Pool for search",
        "capabilities": ["papers", "journals", "wiley_tdm_fulltext_pdf", "bibtex"],
        "live_without_key": True,
        "env_var": "WILEY_TDM_TOKEN",
    },
    {
        "id": "springer_nature",
        "name": "Springer Nature Meta v2, Open Access JATS & Full-Text TDM API",
        "category": "Major Academic Publisher (Nature, Springer, BMC)",
        "corpus_size": "19.06M+ DOIs, 16M+ Meta v2 docs, 1.5M+ Open Access JATS XML full-text articles",
        "base_url": "https://api.springernature.com/meta/v2/json & /openaccess/jats & /xmldata/jats",
        "auth": "?api_key=$SPRINGER_API_KEY; zero-key search via Crossref Member 297 + OpenAlex",
        "rate_limit": "500-5,000 calls/day on free developer tier",
        "capabilities": ["papers", "oa_jats_xml_fulltext", "tdm_xmldata_jats", "bibtex"],
        "live_without_key": True,
        "env_var": "SPRINGER_API_KEY",
    },
    {
        "id": "ieee_xplore",
        "name": "IEEE Xplore Metadata & Full-Text API v1",
        "category": "Electrical Engineering, Computer Science & Standards Publisher",
        "corpus_size": "6.25M+ IEEE transactions, journals, conference papers & standards",
        "base_url": "https://ieeexploreapi.ieee.org/api/v1/search/articles",
        "auth": "?apikey=$IEEE_API_KEY; zero-key search via Crossref Member 263 + OpenAlex",
        "rate_limit": "10 RPS, 200 calls/day default developer tier",
        "capabilities": ["papers", "standards", "oa_fulltext", "bibtex"],
        "live_without_key": True,
        "env_var": "IEEE_API_KEY",
    },
    {
        "id": "arxiv",
        "name": "arXiv API + arXiv HTML / ar5iv + BibTeX",
        "category": "STEM Preprint Server & Full-Text LaTeXML",
        "corpus_size": "2.6M+ preprints (CS, Math, Physics, Q-Bio, Stat, Econ)",
        "base_url": "https://export.arxiv.org/api/query",
        "auth": "None required",
        "rate_limit": "1 request every 3 seconds (0.33 RPS), single concurrent connection",
        "capabilities": ["papers", "bibtex", "html_fulltext_sections", "oa_pdf"],
        "live_without_key": True,
    },
    {
        "id": "pubmed_europepmc",
        "name": "PubMed (NCBI E-utilities) + Europe PMC + PMC BioC Full-Text JSON",
        "category": "Biomedical & Life Sciences Literature",
        "corpus_size": "36M+ PubMed citations, 10.2M+ full-text articles, 6.5M+ OA BioC JSON",
        "base_url": "https://www.ebi.ac.uk/europepmc/webservices/rest",
        "auth": "None required (NCBI E-utilities: 3 RPS no key, 10 RPS with NCBI_API_KEY)",
        "rate_limit": "Europe PMC: high-throughput REST; NCBI: 3-10 RPS",
        "capabilities": ["papers", "mesh_terms", "pmc_bioc_fulltext_sections", "citations", "oa_pdf"],
        "live_without_key": True,
    },
    {
        "id": "pubtator3",
        "name": "NCBI PubTator 3.0 Biomedical Entity & Relation API",
        "category": "Biomedical AI Entity/Relation Search",
        "corpus_size": "1B+ entity/relation annotations across 36M abstracts & 6M PMC full texts",
        "base_url": "https://www.ncbi.nlm.nih.gov/research/pubtator3-api",
        "auth": "None required",
        "rate_limit": "3 RPS",
        "capabilities": ["entity_resolution", "relation_search", "biocjson_fulltext_annotations"],
        "live_without_key": True,
    },
    {
        "id": "doaj",
        "name": "DOAJ (Directory of Open Access Journals) API v4",
        "category": "Open Access Journal & Article Directory",
        "corpus_size": "21,000+ peer-reviewed OA journals, 10.5M+ articles",
        "base_url": "https://doaj.org/api/v4",
        "auth": "None required",
        "rate_limit": "Public REST access",
        "capabilities": ["journals", "papers", "apc_fees", "oa_licenses", "issn_lookup"],
        "live_without_key": True,
    },
    {
        "id": "dblp",
        "name": "DBLP Computer Science Bibliography",
        "category": "Computer Science Papers, Conferences & Journals",
        "corpus_size": "7.5M+ CS publications, 6,000+ venues",
        "base_url": "https://dblp.org/search",
        "auth": "None required (automatic Anubis v1.27.0 metarefresh solver)",
        "rate_limit": "Polite sequential access (~1-2 RPS)",
        "capabilities": ["papers", "journals_venues", "canonical_bibtex"],
        "live_without_key": True,
    },
    {
        "id": "inspire_hep",
        "name": "INSPIRE-HEP REST API",
        "category": "High-Energy Physics, Cosmology & Mathematics",
        "corpus_size": "1.7M+ HEP literature records",
        "base_url": "https://inspirehep.net/api",
        "auth": "None required",
        "rate_limit": "15 requests per 5-second window (3 RPS) per IP",
        "capabilities": ["papers", "journals", "bibtex", "latex_eu_us_citations", "citations"],
        "live_without_key": True,
    },
    {
        "id": "unpaywall",
        "name": "Unpaywall API v2",
        "category": "Legal Open-Access PDF Resolver",
        "corpus_size": "50M+ free full-text scholarly articles across 50,000+ repositories",
        "base_url": "https://api.unpaywall.org/v2",
        "auth": "?email=YOUR_EMAIL query parameter required",
        "rate_limit": "100,000 calls per day (Note: /v2/search retired Sept 18, 2026)",
        "capabilities": ["oa_pdf_resolution", "oa_version_license"],
        "live_without_key": True,
    },
    {
        "id": "opencitations",
        "name": "OpenCitations Index v2 & Meta v1 API",
        "category": "Open Citation Graph (COCI)",
        "corpus_size": "2B+ open citation links",
        "base_url": "https://api.opencitations.net/index/v2",
        "auth": "None required (optional Authorization token)",
        "rate_limit": "High-throughput public access",
        "capabilities": ["citations", "references", "citation_count", "metadata"],
        "live_without_key": True,
    },
    {
        "id": "taylor_francis_sage_oup_cup_acm_acs_aps",
        "name": "Major Society & University Press Publishers (Taylor & Francis, SAGE, OUP, CUP, ACM, ACS, APS, IOP, RSC, MDPI, Frontiers, PLOS)",
        "category": "Publisher-Scoped Crossref Member & OpenAlex Search",
        "corpus_size": "35M+ combined publisher DOIs",
        "base_url": "https://api.crossref.org/v1/members/{member_id}/works",
        "auth": "None required for search & BibTeX; Unpaywall/OpenAlex OA PDF resolution",
        "rate_limit": "3 RPS Polite Pool search; 10 RPS singleton DOI lookup",
        "capabilities": ["papers", "journals", "bibtex", "oa_pdf"],
        "live_without_key": True,
    },
    {
        "id": "datacite",
        "name": "DataCite REST & GraphQL API",
        "category": "Research Datasets, Software, Preprints & Grey Literature",
        "corpus_size": "60M+ DataCite DOIs",
        "base_url": "https://api.datacite.org/dois",
        "auth": "None required",
        "rate_limit": "Public JSON:API access",
        "capabilities": ["datasets_preprints", "bibtex_negotiation", "citations"],
        "live_without_key": True,
    },
    {
        "id": "openaire",
        "name": "OpenAIRE Graph API",
        "category": "European & Global Open Science Graph",
        "corpus_size": "175M+ research products, 3M+ grants/projects",
        "base_url": "https://api.openaire.eu/graph/v1",
        "auth": "None required (optional Bearer token for higher quota)",
        "rate_limit": "Public tier available",
        "capabilities": ["papers", "datasets", "funding_projects"],
        "live_without_key": True,
    },
    {
        "id": "biorxiv_medrxiv",
        "name": "bioRxiv & medRxiv CSHL API",
        "category": "Biology & Health Sciences Preprints",
        "corpus_size": "300K+ preprints with published DOI cross-links",
        "base_url": "https://api.biorxiv.org",
        "auth": "None required",
        "rate_limit": "Public cursor pagination (100 records/page)",
        "capabilities": ["preprint_details", "preprint_to_published_doi"],
        "live_without_key": True,
    },
    {
        "id": "hal_zenodo",
        "name": "HAL Open Archive & Zenodo REST API",
        "category": "Multidisciplinary Open Repositories",
        "corpus_size": "4M+ HAL records, 4M+ Zenodo records",
        "base_url": "https://api.hal.science/search/ & https://zenodo.org/api/records",
        "auth": "None required for search",
        "rate_limit": "Zenodo: 60 RPM guest / 100 RPM token; HAL: public Solr API",
        "capabilities": ["papers", "bibtex", "tei_xml_fulltext", "oa_pdf"],
        "live_without_key": True,
    },
    {
        "id": "core",
        "name": "CORE API v3",
        "category": "Full-Text Open Access Aggregator",
        "corpus_size": "452M+ metadata records, 57M+ hosted full texts",
        "base_url": "https://api.core.ac.uk/v3",
        "auth": "Authorization: Bearer $CORE_API_KEY (or limited guest)",
        "rate_limit": "0.5 RPS guest; 10 RPM registered academic",
        "capabilities": ["papers", "inline_fulltext"],
        "live_without_key": False,
        "env_var": "CORE_API_KEY",
    },
    {
        "id": "nasa_ads",
        "name": "NASA ADS (Astrophysics Data System) API v1",
        "category": "Astronomy, Astrophysics & Physics",
        "corpus_size": "16M+ physics & astronomy records",
        "base_url": "https://api.adsabs.harvard.edu/v1",
        "auth": "Authorization: Bearer $ADS_API_KEY",
        "rate_limit": "5,000 requests/day per key",
        "capabilities": ["papers", "bibtex_export", "citation_metrics"],
        "live_without_key": False,
        "env_var": "ADS_API_KEY",
    },
    {
        "id": "consensus",
        "name": "Consensus MCP & Quick Search API",
        "category": "AI-Native Evidence & Study-Design Search",
        "corpus_size": "200M+ papers with RCT, sample-size & SJR quartile filters",
        "base_url": "https://mcp.consensus.app/mcp",
        "auth": "Bearer $CONSENSUS_API_KEY or OAuth",
        "rate_limit": "1 RPS",
        "capabilities": ["study_design_filtering", "sjr_quartile_filter", "evidence_takeaways"],
        "live_without_key": False,
        "env_var": "CONSENSUS_API_KEY",
    },
    {
        "id": "scite",
        "name": "scite Smart Citations MCP",
        "category": "Citation Context & Regulatory Evidence Intelligence",
        "corpus_size": "1.6B+ supporting/contrasting/mentioning citation statements",
        "base_url": "https://api.scite.ai/mcp",
        "auth": "Bearer $SCITE_API_KEY (scite_...)",
        "rate_limit": "Monthly plan quota",
        "capabilities": ["smart_citations", "supporting_contrasting_snippets", "fda_clinical_trials"],
        "live_without_key": False,
        "env_var": "SCITE_API_KEY",
    },
    {
        "id": "elicit",
        "name": "Elicit v2 REST API & MCP",
        "category": "AI Systematic Reviews & Structured Data Extraction",
        "corpus_size": "138M+ papers, 545K+ clinical trials",
        "base_url": "https://elicit.com/api/v2",
        "auth": "Bearer $ELICIT_API_KEY",
        "rate_limit": "100 RPM per IP (5-min IP ban if exceeded)",
        "capabilities": ["papers", "trials", "systematic_reviews", "research_reports"],
        "live_without_key": False,
        "env_var": "ELICIT_API_KEY",
    },
]


async def search_publisher_by_member(
    client: httpx.AsyncClient,
    publisher_key: str,
    query: str,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    issn: Optional[str] = None,
    limit: int = 10,
    mailto: str = "research-agent@example.org",
) -> List[PaperRecord]:
    """
    Searches a specific academic publisher's full DOI catalog via its official
    Crossref Member ID (e.g., Wiley=311, Elsevier=78, Springer Nature=297, IEEE=263,
    Taylor & Francis=301, SAGE=179, OUP=286, CUP=56, ACM=320, ACS=316, APS=16).
    """
    key_norm = publisher_key.lower().strip()
    if key_norm not in PUBLISHER_CROSSREF_MEMBERS:
        return []
    member_id, _ = PUBLISHER_CROSSREF_MEMBERS[key_norm]

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

    resp = await client.get(
        f"https://api.crossref.org/v1/members/{member_id}/works",
        params=params,
        timeout=15.0,
    )
    if resp.status_code != 200:
        return []
    items = (resp.json().get("message") or {}).get("items") or []
    records: List[PaperRecord] = []
    for it in items[:limit]:
        p = _parse_crossref_work(it)
        p.source_providers = [key_norm]
        # Attach Wiley TDM API full-text endpoint hint if Wiley DOI
        if key_norm == "wiley" and p.doi and not p.pdf_url:
            if os.environ.get("WILEY_TDM_TOKEN") or os.environ.get("TDM_API_TOKEN"):
                p.pdf_url = f"https://api.wiley.com/onlinelibrary/tdm/v1/articles/{quote(p.doi, safe='')}"
        records.append(p)
    return records


# ============================================================================
# 1. ELSEVIER / SCOPUS / SCIENCEDIRECT / SERIAL TITLE APIs
# ============================================================================

async def search_scopus_or_elsevier(
    client: httpx.AsyncClient,
    query: str,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    issn: Optional[str] = None,
    open_access_only: bool = False,
    limit: int = 10,
    api_key: Optional[str] = None,
    insttoken: Optional[str] = None,
    mailto: str = "research-agent@example.org",
) -> List[PaperRecord]:
    """
    Queries the official Elsevier Scopus Search API (/content/search/scopus) if
    ELSEVIER_API_KEY is configured; otherwise falls back seamlessly to Elsevier's
    Crossref Member 78 catalog (25.5M+ ScienceDirect/Elsevier DOIs).
    """
    key = api_key or os.environ.get("ELSEVIER_API_KEY") or os.environ.get("SCOPUS_API_KEY")
    token = insttoken or os.environ.get("ELSEVIER_INSTTOKEN")
    if not key:
        return await search_publisher_by_member(
            client, "elsevier", query, year_min=year_min, year_max=year_max, issn=issn, limit=limit, mailto=mailto
        )

    q_clauses = [f"TITLE-ABS-KEY({query})"]
    if year_min:
        q_clauses.append(f"PUBYEAR > {year_min - 1}")
    if year_max:
        q_clauses.append(f"PUBYEAR < {year_max + 1}")
    if issn:
        q_clauses.append(f"ISSN({issn})")
    if open_access_only:
        q_clauses.append("OPENACCESS(1)")

    headers = {"X-ELS-APIKey": key, "Accept": "application/json"}
    if token:
        headers["X-ELS-Insttoken"] = token

    resp = await client.get(
        "https://api.elsevier.com/content/search/scopus",
        params={"query": " AND ".join(q_clauses), "count": min(max(limit, 1), 25)},
        headers=headers,
        timeout=15.0,
    )
    if resp.status_code != 200:
        return await search_publisher_by_member(
            client, "elsevier", query, year_min=year_min, year_max=year_max, issn=issn, limit=limit, mailto=mailto
        )

    entries = ((resp.json().get("search-results") or {}).get("entry")) or []
    papers: List[PaperRecord] = []
    for e in entries[:limit]:
        if e.get("error"):
            continue
        doi = clean_doi(e.get("prism:doi"))
        scopus_id = (e.get("dc:identifier") or "").replace("SCOPUS_ID:", "")
        title = e.get("dc:title") or "Untitled"
        creator = e.get("dc:creator")
        authors = [AuthorRecord(name=creator)] if creator else []
        cov_date = e.get("prism:coverDate") or ""
        year = int(cov_date[:4]) if len(cov_date) >= 4 and cov_date[:4].isdigit() else None
        j_name = e.get("prism:publicationName")
        p_issn = e.get("prism:issn")
        e_issn = e.get("prism:eIssn")
        issns = [i for i in (p_issn, e_issn) if i]
        cited_by = e.get("citedby-count")
        is_oa = str(e.get("openaccess", "0")) == "1"
        papers.append(
            PaperRecord(
                id=f"scopus:{scopus_id}" if scopus_id else f"doi:{doi}",
                title=title,
                doi=doi,
                authors=authors,
                year=year,
                publication_date=cov_date or None,
                publication_type=e.get("prism:aggregationType"),
                journal=JournalSummary(name=j_name, issn_l=issns[0] if issns else None, issns=issns, is_oa=is_oa)
                if j_name
                else None,
                volume=e.get("prism:volume"),
                issue=e.get("prism:issueIdentifier"),
                pages=e.get("prism:pageRange"),
                abstract=e.get("dc:description"),
                citation_count=int(cited_by) if str(cited_by).isdigit() else None,
                is_oa=is_oa,
                landing_page_url=f"https://doi.org/{doi}" if doi else None,
                source_providers=["scopus"],
            )
        )
    return papers


async def enrich_journal_elsevier_serial(
    client: httpx.AsyncClient,
    issn: str,
    api_key: Optional[str] = None,
) -> Optional[JournalMetrics]:
    """Queries Elsevier Serial Title API for CiteScore, SJR, and SNIP if ELSEVIER_API_KEY is configured."""
    key = api_key or os.environ.get("ELSEVIER_API_KEY") or os.environ.get("SCOPUS_API_KEY")
    if not key or not issn:
        return None
    resp = await client.get(
        f"https://api.elsevier.com/content/serial/title/issn/{issn}",
        headers={"X-ELS-APIKey": key, "Accept": "application/json"},
        timeout=10.0,
    )
    if resp.status_code != 200:
        return None
    entries = (resp.json().get("serial-metadata-response") or {}).get("entry") or []
    if not entries:
        return None
    entry = entries[0]
    citescore_info = entry.get("citeScoreYearInfoList") or {}
    cs_val = citescore_info.get("citeScoreCurrentMetric")
    sjr_list = (entry.get("SJRList") or {}).get("SJR") or []
    sjr_val = sjr_list[0].get("$") if sjr_list and isinstance(sjr_list[0], dict) else None
    snip_list = (entry.get("SNIPList") or {}).get("SNIP") or []
    snip_val = snip_list[0].get("$") if snip_list and isinstance(snip_list[0], dict) else None
    return JournalMetrics(
        citescore=float(cs_val) if cs_val else None,
        sjr=float(sjr_val) if sjr_val else None,
        snip=float(snip_val) if snip_val else None,
    )


async def extract_sciencedirect_fulltext(
    client: httpx.AsyncClient,
    doi: str,
    focus_query: Optional[str] = None,
    max_chars: int = 12000,
    api_key: Optional[str] = None,
    insttoken: Optional[str] = None,
) -> Tuple[List[Dict[str, str]], List[ContextSnippet], Optional[str]]:
    """
    Fetches full-text article content from Elsevier ScienceDirect Article Retrieval API
    (https://api.elsevier.com/content/article/doi/{doi}?view=FULL) when ELSEVIER_API_KEY is set.
    """
    key = api_key or os.environ.get("ELSEVIER_API_KEY") or os.environ.get("SCOPUS_API_KEY")
    if not key or not doi:
        return ([], [], None)
    headers = {"X-ELS-APIKey": key, "Accept": "application/json"}
    token = insttoken or os.environ.get("ELSEVIER_INSTTOKEN")
    if token:
        headers["X-ELS-Insttoken"] = token

    try:
        resp = await client.get(
            f"https://api.elsevier.com/content/article/doi/{doi}",
            params={"view": "FULL"},
            headers=headers,
            timeout=14.0,
        )
        if resp.status_code != 200:
            return ([], [], None)
        data = resp.json().get("full-text-retrieval-response") or {}
        original_text = data.get("originalText") or ""
        if len(original_text) < 100:
            return ([], [], None)
        clean_text = re.sub(r"\s+", " ", original_text).strip()
        sections = [{"heading": "ScienceDirect Full Text", "content": clean_text[:max_chars]}]
        snippets = [
            ContextSnippet(
                section="ScienceDirect Full Text",
                text=clean_text[:1500],
                source="elsevier_sciencedirect_api",
            )
        ]
        return (sections, snippets, clean_text[:max_chars])
    except Exception:
        return ([], [], None)


# ============================================================================
# 2. CLARIVATE WEB OF SCIENCE (STARTER v1, EXPANDED & JCR JOURNALS v1)
# ============================================================================

async def search_wos_documents(
    client: httpx.AsyncClient,
    query: str,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    issn: Optional[str] = None,
    limit: int = 10,
    api_key: Optional[str] = None,
) -> List[PaperRecord]:
    """
    Queries Clarivate Web of Science Starter API v1 (/apis/wos-starter/v1/documents)
    with fallback to Web of Science Expanded API (/api/wos) if WOS_API_KEY is configured.
    """
    key = api_key or os.environ.get("WOS_API_KEY") or os.environ.get("CLARIVATE_API_KEY")
    if not key:
        return []

    q_parts = [f"TS=({query})"]
    if year_min and year_max:
        q_parts.append(f"PY=({year_min}-{year_max})")
    elif year_min:
        q_parts.append(f"PY=({year_min}-2026)")
    elif year_max:
        q_parts.append(f"PY=(1900-{year_max})")
    if issn:
        q_parts.append(f"IS=({issn})")
    wos_query = " AND ".join(q_parts)

    headers = {"X-ApiKey": key, "Accept": "application/json"}
    resp = await client.get(
        "https://api.clarivate.com/apis/wos-starter/v1/documents",
        params={"db": "WOS", "q": wos_query, "limit": min(max(limit, 1), 50)},
        headers=headers,
        timeout=15.0,
    )
    if resp.status_code != 200:
        return []

    hits = resp.json().get("hits") or []
    papers: List[PaperRecord] = []
    for h in hits[:limit]:
        uid = h.get("uid") or ""
        title = h.get("title") or "Untitled"
        idents = h.get("identifiers") or {}
        doi = clean_doi(idents.get("doi"))
        pmid = str(idents.get("pmid")) if idents.get("pmid") else None
        issn_val = idents.get("issn") or idents.get("eissn")
        issns = [i for i in (idents.get("issn"), idents.get("eissn")) if i]
        names = (h.get("names") or {}).get("authors") or []
        authors = [AuthorRecord(name=a.get("displayName")) for a in names if a.get("displayName")]
        src = h.get("source") or {}
        year = src.get("publishYear")
        cites_list = h.get("citations") or []
        cit_count = cites_list[0].get("count") if cites_list else None
        papers.append(
            PaperRecord(
                id=f"wos:{uid}" if uid else f"doi:{doi}",
                title=title,
                doi=doi,
                pmid=pmid,
                authors=authors,
                year=int(year) if str(year).isdigit() else None,
                publication_type=(h.get("types") or [None])[0],
                journal=JournalSummary(name=src.get("sourceTitle"), issn_l=issn_val, issns=issns)
                if src.get("sourceTitle")
                else None,
                volume=src.get("volume"),
                issue=src.get("issue"),
                pages=(src.get("pages") or {}).get("range"),
                citation_count=cit_count,
                landing_page_url=(h.get("links") or {}).get("record"),
                source_providers=["clarivate_wos"],
            )
        )
    return papers


async def enrich_journal_wos_jcr(
    client: httpx.AsyncClient,
    issn: str,
    api_key: Optional[str] = None,
) -> Optional[JournalMetrics]:
    """
    Queries Clarivate Web of Science Journals API (JCR v1: /apis/wos-journals/v1/journals)
    to retrieve Journal Impact Factor (JIF), JCI, and JIF Quartile when WOS_API_KEY is set.
    """
    key = api_key or os.environ.get("WOS_API_KEY") or os.environ.get("CLARIVATE_API_KEY")
    if not key or not issn:
        return None
    headers = {"X-ApiKey": key, "Accept": "application/json"}
    try:
        resp = await client.get(
            "https://api.clarivate.com/apis/wos-journals/v1/journals",
            params={"q": issn, "limit": 1},
            headers=headers,
            timeout=10.0,
        )
        if resp.status_code != 200:
            return None
        hits = resp.json().get("hits") or []
        if not hits:
            return None
        j_id = hits[0].get("id")
        if not j_id:
            return None
        rep = await client.get(
            f"https://api.clarivate.com/apis/wos-journals/v1/journals/{j_id}/reports/year/2025",
            headers=headers,
            timeout=10.0,
        )
        if rep.status_code != 200:
            return None
        r_data = rep.json()
        metrics_obj = (r_data.get("metrics") or {}).get("impactMetrics") or {}
        ranks_list = r_data.get("ranks") or []
        q_val = ranks_list[0].get("quartile") if ranks_list else None
        pct_val = ranks_list[0].get("jifPercentile") if ranks_list else None
        return JournalMetrics(
            jif=float(metrics_obj["jif"]) if metrics_obj.get("jif") else None,
            jci=float(metrics_obj["jci"]) if metrics_obj.get("jci") else None,
            jif_quartile=q_val,
            jif_percentile=float(pct_val) if pct_val else None,
        )
    except Exception:
        return None


# ============================================================================
# 3. WILEY ONLINE LIBRARY TDM API v1
# ============================================================================

async def extract_wiley_tdm_pdf_context(
    client: httpx.AsyncClient,
    doi: str,
    focus_query: Optional[str] = None,
    max_chars: int = 12000,
    tdm_token: Optional[str] = None,
) -> Tuple[List[Dict[str, str]], List[ContextSnippet], Optional[str]]:
    """
    Downloads full-text PDF directly from Wiley's Text and Data Mining (TDM) API
    (GET https://api.wiley.com/onlinelibrary/tdm/v1/articles/{doi} with header
    Wiley-TDM-Client-Token) and extracts structured page context via pypdf.
    """
    token = tdm_token or os.environ.get("WILEY_TDM_TOKEN") or os.environ.get("TDM_API_TOKEN")
    cleaned = clean_doi(doi)
    if not token or not cleaned:
        return ([], [], None)

    encoded_doi = quote(cleaned, safe="")
    url = f"https://api.wiley.com/onlinelibrary/tdm/v1/articles/{encoded_doi}"
    try:
        resp = await client.get(
            url,
            headers={"Wiley-TDM-Client-Token": token, "Accept": "application/pdf"},
            follow_redirects=True,
            timeout=20.0,
        )
        if resp.status_code != 200 or not resp.content.startswith(b"%PDF"):
            return ([], [], None)
        reader = PdfReader(io.BytesIO(resp.content))
    except Exception:
        return ([], [], None)

    sections: List[Dict[str, str]] = []
    snippets: List[ContextSnippet] = []
    query_terms = [t.lower() for t in re.findall(r"[a-zA-Z0-9]{3,}", focus_query or "")]

    for idx in range(min(len(reader.pages), 25)):
        try:
            txt = re.sub(r"\s+", " ", reader.pages[idx].extract_text() or "").strip()
            if len(txt) < 40:
                continue
            label = f"Wiley TDM PDF Page {idx + 1}"
            sections.append({"heading": label, "content": txt[:2000]})
            if query_terms:
                hits = sum(1 for qt in query_terms if qt in txt.lower())
                if hits > 0:
                    snippets.append(
                        ContextSnippet(
                            section=label,
                            text=txt[:1200],
                            source="wiley_tdm_pdf_api",
                            score=float(hits) / len(query_terms),
                        )
                    )
        except Exception:
            continue

    snippets.sort(key=lambda s: s.score or 0.0, reverse=True)
    full_excerpt = "\n\n".join(f"### {s['heading']}\n{s['content']}" for s in sections)[:max_chars]
    return (sections[:10], snippets[:8], full_excerpt or None)


# ============================================================================
# 4. SPRINGER NATURE META v2, OPEN ACCESS JATS & TDM API
# ============================================================================

async def search_springer_nature(
    client: httpx.AsyncClient,
    query: str,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    issn: Optional[str] = None,
    open_access_only: bool = False,
    limit: int = 10,
    api_key: Optional[str] = None,
    mailto: str = "research-agent@example.org",
) -> List[PaperRecord]:
    """
    Queries Springer Nature Meta v2 / OpenAccess JSON API when SPRINGER_API_KEY is set,
    otherwise falls back to Crossref Member 297 (Springer Nature's 19.06M+ DOIs).
    """
    key = api_key or os.environ.get("SPRINGER_API_KEY")
    if not key:
        return await search_publisher_by_member(
            client, "springer_nature", query, year_min=year_min, year_max=year_max, issn=issn, limit=limit, mailto=mailto
        )

    endpoint = (
        "https://api.springernature.com/openaccess/json"
        if open_access_only
        else "https://api.springernature.com/meta/v2/json"
    )
    q_parts = [query]
    if year_min:
        q_parts.append(f"onlinedatefrom:{year_min}-01-01")
    if year_max:
        q_parts.append(f"onlinedateto:{year_max}-12-31")
    if issn:
        q_parts.append(f"issn:{issn}")

    resp = await client.get(
        endpoint,
        params={"q": " ".join(q_parts), "p": min(max(limit, 1), 50), "api_key": key},
        timeout=15.0,
    )
    if resp.status_code != 200:
        return await search_publisher_by_member(
            client, "springer_nature", query, year_min=year_min, year_max=year_max, issn=issn, limit=limit, mailto=mailto
        )

    records_raw = resp.json().get("records") or []
    papers: List[PaperRecord] = []
    for r in records_raw[:limit]:
        doi = clean_doi(r.get("doi"))
        authors = [AuthorRecord(name=c.get("creator")) for c in (r.get("creators") or []) if c.get("creator")]
        pub_date = r.get("publicationDate") or ""
        year = int(pub_date[:4]) if len(pub_date) >= 4 and pub_date[:4].isdigit() else None
        j_name = r.get("publicationName")
        issn_val = r.get("issn") or r.get("eIssn")
        issns = [i for i in (r.get("issn"), r.get("eIssn")) if i]
        is_oa = str(r.get("openaccess", "")).lower() == "true" or open_access_only
        papers.append(
            PaperRecord(
                id=f"doi:{doi}" if doi else f"springer:{r.get('identifier', '')}",
                title=r.get("title") or "Untitled",
                doi=doi,
                authors=authors,
                year=year,
                publication_date=pub_date or None,
                publication_type=r.get("contentType"),
                journal=JournalSummary(name=j_name, issn_l=issn_val, issns=issns, publisher=r.get("publisher"), is_oa=is_oa)
                if j_name
                else None,
                volume=r.get("volume"),
                issue=r.get("number"),
                pages=f"{r.get('startingPage', '')}-{r.get('endingPage', '')}".strip("-") or None,
                abstract=r.get("abstract"),
                is_oa=is_oa,
                landing_page_url=f"https://doi.org/{doi}" if doi else None,
                source_providers=["springer_nature"],
            )
        )
    return papers


async def extract_springer_jats_context(
    client: httpx.AsyncClient,
    doi: str,
    focus_query: Optional[str] = None,
    max_chars: int = 12000,
    api_key: Optional[str] = None,
) -> Tuple[List[Dict[str, str]], List[ContextSnippet], Optional[str]]:
    """
    Fetches full-text JATS XML from Springer Nature Open Access API (/openaccess/jats)
    or TDM Full-Text API (/xmldata/jats) when SPRINGER_API_KEY is configured.
    """
    key = api_key or os.environ.get("SPRINGER_API_KEY")
    cleaned = clean_doi(doi)
    if not key or not cleaned:
        return ([], [], None)

    for endpoint in ("https://api.springernature.com/openaccess/jats", "https://api.springernature.com/xmldata/jats"):
        try:
            resp = await client.get(endpoint, params={"q": f"doi:{cleaned}", "api_key": key}, timeout=14.0)
            if resp.status_code == 200 and "<body" in resp.text:
                soup = BeautifulSoup(resp.text, "lxml-xml")
                sections: List[Dict[str, str]] = []
                snippets: List[ContextSnippet] = []
                for sec in soup.find_all("sec"):
                    t_el = sec.find("title")
                    heading = t_el.get_text(" ", strip=True) if t_el else "Section"
                    body = " ".join(p.get_text(" ", strip=True) for p in sec.find_all("p", recursive=False))
                    if len(body) > 40:
                        sections.append({"heading": heading, "content": body[:2000]})
                        snippets.append(ContextSnippet(section=heading, text=body[:1200], source="springer_jats_xml"))
                if sections:
                    excerpt = "\n\n".join(f"### {s['heading']}\n{s['content']}" for s in sections)[:max_chars]
                    return (sections[:10], snippets[:8], excerpt)
        except Exception:
            continue
    return ([], [], None)


# ============================================================================
# 5. IEEE XPLORE METADATA & OPEN ACCESS API v1
# ============================================================================

async def search_ieee_xplore(
    client: httpx.AsyncClient,
    query: str,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    issn: Optional[str] = None,
    open_access_only: bool = False,
    limit: int = 10,
    api_key: Optional[str] = None,
    mailto: str = "research-agent@example.org",
) -> List[PaperRecord]:
    """
    Queries IEEE Xplore Metadata API v1 (https://ieeexploreapi.ieee.org/api/v1/search/articles)
    when IEEE_API_KEY is set, otherwise falls back to Crossref Member 263 (6.25M+ IEEE works).
    """
    key = api_key or os.environ.get("IEEE_API_KEY")
    if not key:
        return await search_publisher_by_member(
            client, "ieee", query, year_min=year_min, year_max=year_max, issn=issn, limit=limit, mailto=mailto
        )

    params: Dict[str, Any] = {
        "querytext": query,
        "max_records": min(max(limit, 1), 200),
        "apikey": key,
    }
    if year_min:
        params["start_year"] = year_min
    if year_max:
        params["end_year"] = year_max
    if issn:
        params["issn"] = issn
    if open_access_only:
        params["open_access"] = "True"

    resp = await client.get("https://ieeexploreapi.ieee.org/api/v1/search/articles", params=params, timeout=15.0)
    if resp.status_code != 200:
        return await search_publisher_by_member(
            client, "ieee", query, year_min=year_min, year_max=year_max, issn=issn, limit=limit, mailto=mailto
        )

    articles = resp.json().get("articles") or []
    papers: List[PaperRecord] = []
    for a in articles[:limit]:
        doi = clean_doi(a.get("doi"))
        authors_raw = ((a.get("authors") or {}).get("authors")) or []
        authors = [AuthorRecord(name=au.get("full_name")) for au in authors_raw if au.get("full_name")]
        is_oa = a.get("access_type") in ("OPEN_ACCESS", "EPHEMERA")
        papers.append(
            PaperRecord(
                id=f"ieee:{a.get('article_number', '')}" if a.get("article_number") else f"doi:{doi}",
                title=a.get("title") or "Untitled",
                doi=doi,
                authors=authors,
                year=a.get("publication_year"),
                publication_date=a.get("publication_date"),
                publication_type=a.get("content_type"),
                journal=JournalSummary(
                    name=a.get("publication_title"),
                    issn_l=a.get("issn"),
                    issns=[a["issn"]] if a.get("issn") else [],
                    publisher=a.get("publisher") or "IEEE",
                    is_oa=is_oa,
                )
                if a.get("publication_title")
                else None,
                volume=a.get("volume"),
                issue=a.get("issue"),
                pages=f"{a.get('start_page', '')}-{a.get('end_page', '')}".strip("-") or None,
                abstract=a.get("abstract"),
                citation_count=a.get("citing_paper_count"),
                is_oa=is_oa,
                pdf_url=a.get("pdf_url") if is_oa else None,
                html_url=a.get("html_url"),
                landing_page_url=a.get("abstract_url") or (f"https://doi.org/{doi}" if doi else None),
                source_providers=["ieee_xplore"],
            )
        )
    return papers


# ============================================================================
# 6. CORE API v3 & NASA ADS API v1
# ============================================================================

async def search_core_works(
    client: httpx.AsyncClient,
    query: str,
    limit: int = 5,
    api_key: Optional[str] = None,
) -> List[PaperRecord]:
    key = api_key or os.environ.get("CORE_API_KEY")
    headers = {"Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    resp = await client.get(
        "https://api.core.ac.uk/v3/search/works",
        params={"q": query, "limit": min(max(limit, 1), 25)},
        headers=headers,
        timeout=12.0,
    )
    if resp.status_code != 200:
        return []
    results = resp.json().get("results") or []
    papers: List[PaperRecord] = []
    for r in results[:limit]:
        doi = clean_doi(r.get("doi"))
        arxiv_id = clean_arxiv_id(r.get("arxivId"))
        authors = [AuthorRecord(name=a.get("name")) for a in (r.get("authors") or []) if a.get("name")]
        journals = r.get("journals") or []
        j_title = journals[0].get("title") if journals else r.get("publisher")
        papers.append(
            PaperRecord(
                id=f"core:{r.get('id')}",
                title=r.get("title") or "Untitled",
                doi=doi,
                arxiv_id=arxiv_id,
                authors=authors,
                year=r.get("yearPublished"),
                journal=JournalSummary(name=j_title, is_oa=True) if j_title else None,
                abstract=r.get("abstract"),
                is_oa=True,
                pdf_url=r.get("downloadUrl"),
                source_providers=["core"],
            )
        )
    return papers
