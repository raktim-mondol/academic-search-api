from __future__ import annotations
import asyncio
import os
from typing import Any, Dict, List, Optional
import httpx
from .models import (
    CitationGraphResult,
    ContextSnippet,
    PaperContextResult,
    PaperRecord,
    SearchJournalsResponse,
    SearchPapersResponse,
)
from .providers import (
    PUBLISHER_CROSSREF_MEMBERS,
    SUPPORTED_DATABASES_CATALOG,
    enrich_journal_elsevier_serial,
    enrich_journal_wos_jcr,
    extract_arxiv_html_context,
    extract_pdf_text_context,
    extract_pmc_bioc_context,
    extract_sciencedirect_fulltext,
    extract_springer_jats_context,
    extract_wiley_tdm_pdf_context,
    fetch_arxiv_bibtex,
    fetch_dblp_bibtex,
    fetch_doi_bibtex,
    fetch_inspire_bibtex,
    get_arxiv_paper,
    get_citations_openalex,
    get_opencitations,
    get_paper_europe_pmc,
    get_paper_s2,
    get_work_crossref,
    get_work_openalex,
    resolve_unpaywall_oa,
    search_articles_doaj,
    search_arxiv,
    search_core_works,
    search_europe_pmc,
    search_ieee_xplore,
    search_journals_crossref,
    search_journals_doaj,
    search_journals_openalex,
    search_papers_dblp,
    search_papers_inspire,
    search_papers_s2,
    search_publisher_by_member,
    search_scopus_or_elsevier,
    search_snippets_s2,
    search_springer_nature,
    search_venues_dblp,
    search_works_crossref,
    search_works_openalex,
    search_wos_documents,
)
from .utils import (
    classify_identifier,
    clean_doi,
    deduplicate_and_merge_journals,
    deduplicate_and_merge_papers,
    merge_two_papers,
    synthesize_bibtex,
)


DEFAULT_PAPER_PROVIDERS = ["openalex", "semantic_scholar", "arxiv", "pubmed_europepmc", "crossref", "dblp"]
DEFAULT_JOURNAL_PROVIDERS = ["openalex", "doaj", "crossref", "dblp"]


class AcademicSearchClient:
    """
    Unified Academic Search SDK for AI Agents and Research Pipelines.
    Queries OpenAlex, Semantic Scholar, Crossref, arXiv, PubMed/Europe PMC,
    DOAJ, DBLP, INSPIRE-HEP, Unpaywall, OpenCitations, Clarivate Web of Science (WoS/JCR),
    Elsevier (Scopus/ScienceDirect/Serial Title), Wiley TDM, Springer Nature, IEEE Xplore,
    and 12+ society/university press publishers (Taylor & Francis, SAGE, OUP, CUP, ACM, ACS, APS, etc.).
    """

    def __init__(
        self,
        mailto: Optional[str] = None,
        openalex_api_key: Optional[str] = None,
        s2_api_key: Optional[str] = None,
        elsevier_api_key: Optional[str] = None,
        wos_api_key: Optional[str] = None,
        wiley_tdm_token: Optional[str] = None,
        springer_api_key: Optional[str] = None,
        ieee_api_key: Optional[str] = None,
        core_api_key: Optional[str] = None,
        timeout: float = 20.0,
    ) -> None:
        self.mailto = mailto or os.environ.get("ACADEMIC_MAILTO", "research-agent@example.org")
        self.openalex_api_key = openalex_api_key or os.environ.get("OPENALEX_API_KEY")
        self.s2_api_key = s2_api_key or os.environ.get("S2_API_KEY") or os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        self.elsevier_api_key = elsevier_api_key or os.environ.get("ELSEVIER_API_KEY") or os.environ.get("SCOPUS_API_KEY")
        self.wos_api_key = wos_api_key or os.environ.get("WOS_API_KEY") or os.environ.get("CLARIVATE_API_KEY")
        self.wiley_tdm_token = wiley_tdm_token or os.environ.get("WILEY_TDM_TOKEN") or os.environ.get("TDM_API_TOKEN")
        self.springer_api_key = springer_api_key or os.environ.get("SPRINGER_API_KEY")
        self.ieee_api_key = ieee_api_key or os.environ.get("IEEE_API_KEY")
        self.core_api_key = core_api_key or os.environ.get("CORE_API_KEY")
        self.timeout = timeout
        self._headers = {"User-Agent": f"AcadSearchUnifiedSDK/1.1 (mailto:{self.mailto})"}

    def list_databases(self) -> List[Dict[str, Any]]:
        return SUPPORTED_DATABASES_CATALOG

    async def asearch_papers(
        self,
        query: str,
        providers: Optional[List[str]] = None,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        open_access_only: bool = False,
        venue: Optional[str] = None,
        min_citations: Optional[int] = None,
        limit: int = 10,
        sort: Optional[str] = None,
        include_bibtex: bool = True,
    ) -> SearchPapersResponse:
        selected = providers or DEFAULT_PAPER_PROVIDERS
        per_prov_limit = min(max(limit, 5), 25)
        warnings: List[str] = []
        venue_issn = venue if venue and "-" in venue and len(venue) == 9 else None

        async with httpx.AsyncClient(headers=self._headers, timeout=self.timeout) as client:
            tasks: Dict[str, Any] = {}
            for prov in selected:
                p = prov.lower().strip()
                if p == "openalex":
                    tasks[p] = search_works_openalex(
                        client,
                        query=query,
                        year_min=year_min,
                        year_max=year_max,
                        open_access_only=open_access_only,
                        venue_issn=venue_issn,
                        min_citations=min_citations,
                        limit=per_prov_limit,
                        sort=sort,
                        api_key=self.openalex_api_key,
                        mailto=self.mailto,
                    )
                elif p in ("semantic_scholar", "s2"):
                    tasks["semantic_scholar"] = search_papers_s2(
                        client,
                        query=query,
                        year_min=year_min,
                        year_max=year_max,
                        open_access_only=open_access_only,
                        venue=venue,
                        min_citations=min_citations,
                        limit=per_prov_limit,
                        api_key=self.s2_api_key,
                    )
                elif p == "crossref":
                    tasks[p] = search_works_crossref(
                        client,
                        query=query,
                        year_min=year_min,
                        year_max=year_max,
                        issn=venue_issn,
                        limit=per_prov_limit,
                        mailto=self.mailto,
                    )
                elif p == "arxiv":
                    tasks[p] = search_arxiv(
                        client,
                        query=query,
                        limit=per_prov_limit,
                        sort_by="submittedDate" if sort == "year" else "relevance",
                    )
                elif p in ("pubmed", "europepmc", "pubmed_europepmc"):
                    tasks["pubmed_europepmc"] = search_europe_pmc(
                        client,
                        query=query,
                        year_min=year_min,
                        year_max=year_max,
                        open_access_only=open_access_only,
                        limit=per_prov_limit,
                    )
                elif p == "dblp":
                    tasks[p] = search_papers_dblp(client, query=query, limit=per_prov_limit)
                elif p == "doaj":
                    tasks[p] = search_articles_doaj(client, query=query, limit=per_prov_limit)
                elif p in ("inspire", "inspire_hep"):
                    tasks["inspire_hep"] = search_papers_inspire(client, query=query, limit=per_prov_limit)
                elif p == "core":
                    tasks[p] = search_core_works(
                        client, query=query, limit=per_prov_limit, api_key=self.core_api_key
                    )
                elif p in ("scopus", "elsevier", "sciencedirect"):
                    tasks[p] = search_scopus_or_elsevier(
                        client,
                        query=query,
                        year_min=year_min,
                        year_max=year_max,
                        issn=venue_issn,
                        open_access_only=open_access_only,
                        limit=per_prov_limit,
                        api_key=self.elsevier_api_key,
                        mailto=self.mailto,
                    )
                elif p in ("wos", "web_of_science", "clarivate"):
                    tasks["clarivate_wos"] = search_wos_documents(
                        client,
                        query=query,
                        year_min=year_min,
                        year_max=year_max,
                        issn=venue_issn,
                        limit=per_prov_limit,
                        api_key=self.wos_api_key,
                    )
                elif p in ("springer", "springer_nature", "nature"):
                    tasks["springer_nature"] = search_springer_nature(
                        client,
                        query=query,
                        year_min=year_min,
                        year_max=year_max,
                        issn=venue_issn,
                        open_access_only=open_access_only,
                        limit=per_prov_limit,
                        api_key=self.springer_api_key,
                        mailto=self.mailto,
                    )
                elif p in ("ieee", "ieee_xplore"):
                    tasks["ieee_xplore"] = search_ieee_xplore(
                        client,
                        query=query,
                        year_min=year_min,
                        year_max=year_max,
                        issn=venue_issn,
                        open_access_only=open_access_only,
                        limit=per_prov_limit,
                        api_key=self.ieee_api_key,
                        mailto=self.mailto,
                    )
                elif p in PUBLISHER_CROSSREF_MEMBERS:
                    tasks[p] = search_publisher_by_member(
                        client,
                        publisher_key=p,
                        query=query,
                        year_min=year_min,
                        year_max=year_max,
                        issn=venue_issn,
                        limit=per_prov_limit,
                        mailto=self.mailto,
                    )

            gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
            all_papers: List[PaperRecord] = []
            for prov_name, res in zip(tasks.keys(), gathered):
                if isinstance(res, Exception):
                    warnings.append(f"{prov_name}: {type(res).__name__}")
                elif isinstance(res, list):
                    all_papers.extend(res)

            merged = deduplicate_and_merge_papers(all_papers)

            q_norm = query.strip().lower()
            if sort == "citations":
                merged.sort(key=lambda x: x.citation_count or 0, reverse=True)
            elif sort == "year":
                merged.sort(key=lambda x: x.year or 0, reverse=True)
            else:
                merged.sort(
                    key=lambda x: (
                        1 if (x.title or "").strip().lower() == q_norm else 0,
                        1 if q_norm in (x.title or "").strip().lower() else 0,
                        len(x.source_providers),
                        1 if x.abstract else 0,
                        x.citation_count or 0,
                    ),
                    reverse=True,
                )

            # Free ($0.00) singleton OpenAlex DOI/arXiv enrichment for any top paper missing OpenAlex metadata
            enrich_targets = [
                p for p in merged if (p.doi or p.arxiv_id) and not p.openalex_id
            ][: max(limit * 2, 10)]
            if enrich_targets:
                oa_lookups = await asyncio.gather(
                    *[
                        get_work_openalex(
                            client,
                            p.doi if p.doi else p.arxiv_id,
                            "doi" if p.doi else "arxiv",
                            self.openalex_api_key,
                            self.mailto,
                        )
                        for p in enrich_targets
                    ],
                    return_exceptions=True,
                )
                for idx_p, oa_res in zip(enrich_targets, oa_lookups):
                    if isinstance(oa_res, PaperRecord):
                        pos = merged.index(idx_p)
                        merged[pos] = merge_two_papers(merged[pos], oa_res)

        filtered: List[PaperRecord] = []
        for paper in merged:
            if year_min and paper.year and paper.year < year_min:
                continue
            if year_max and paper.year and paper.year > year_max:
                continue
            if open_access_only and paper.is_oa is False and not paper.pdf_url:
                continue
            if min_citations and (paper.citation_count or 0) < min_citations:
                continue
            if include_bibtex and not paper.bibtex:
                paper.bibtex = synthesize_bibtex(paper)
            filtered.append(paper)

        if sort == "citations":
            filtered.sort(key=lambda x: x.citation_count or 0, reverse=True)
        elif sort == "year":
            filtered.sort(key=lambda x: x.year or 0, reverse=True)

        final_results = filtered[:limit]
        return SearchPapersResponse(
            query=query,
            total_returned=len(final_results),
            providers_queried=list(tasks.keys()),
            results=final_results,
            warnings=warnings,
        )

    async def asearch_journals(
        self,
        query: Optional[str] = None,
        issn: Optional[str] = None,
        open_access_only: bool = False,
        providers: Optional[List[str]] = None,
        limit: int = 10,
    ) -> SearchJournalsResponse:
        selected = providers or DEFAULT_JOURNAL_PROVIDERS
        warnings: List[str] = []

        async with httpx.AsyncClient(headers=self._headers, timeout=self.timeout) as client:
            tasks: Dict[str, Any] = {}
            for prov in selected:
                p = prov.lower().strip()
                if p == "openalex":
                    tasks[p] = search_journals_openalex(
                        client,
                        query=query,
                        issn=issn,
                        open_access_only=open_access_only,
                        limit=limit,
                        api_key=self.openalex_api_key,
                        mailto=self.mailto,
                    )
                elif p == "doaj":
                    tasks[p] = search_journals_doaj(client, query=query, issn=issn, limit=limit)
                elif p == "crossref" and not open_access_only:
                    tasks[p] = search_journals_crossref(
                        client, query=query, issn=issn, limit=limit, mailto=self.mailto
                    )
                elif p == "dblp" and query and not issn and not open_access_only:
                    tasks[p] = search_venues_dblp(client, query=query, limit=limit)

            gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
            all_journals = []
            for prov_name, res in zip(tasks.keys(), gathered):
                if isinstance(res, Exception):
                    warnings.append(f"{prov_name}: {type(res).__name__}")
                elif isinstance(res, list):
                    all_journals.extend(res)

            merged = deduplicate_and_merge_journals(all_journals)
            if query:
                jq_norm = query.strip().lower()
                merged.sort(
                    key=lambda j: (
                        2 if (j.title or "").strip().lower() == jq_norm else (1 if jq_norm in (j.title or "").strip().lower() else 0),
                        len(j.source_providers),
                        j.metrics.works_count or 0,
                    ),
                    reverse=True,
                )

            # Enrich any journal that has an ISSN via OpenAlex's free ($0.00) singleton /sources/issn:{issn} endpoint
            need_oa_metrics = [
                j
                for j in merged[:limit]
                if (j.issn_l or j.issns) and j.metrics.two_year_mean_citedness is None
            ][:8]
            if need_oa_metrics:
                oa_src_tasks = [
                    search_journals_openalex(
                        client,
                        query=None,
                        issn=j.issn_l or j.issns[0],
                        limit=1,
                        api_key=self.openalex_api_key,
                        mailto=self.mailto,
                    )
                    for j in need_oa_metrics
                ]
                oa_src_results = await asyncio.gather(*oa_src_tasks, return_exceptions=True)
                for j_target, oa_res in zip(need_oa_metrics, oa_src_results):
                    if isinstance(oa_res, list) and oa_res:
                        oa_j = oa_res[0]
                        j_target.metrics.two_year_mean_citedness = oa_j.metrics.two_year_mean_citedness
                        j_target.metrics.h_index = oa_j.metrics.h_index
                        j_target.metrics.i10_index = oa_j.metrics.i10_index
                        j_target.metrics.works_count = j_target.metrics.works_count or oa_j.metrics.works_count
                        j_target.metrics.cited_by_count = oa_j.metrics.cited_by_count
                        if j_target.is_oa is None:
                            j_target.is_oa = oa_j.is_oa
                        if j_target.is_in_doaj is None:
                            j_target.is_in_doaj = oa_j.is_in_doaj
                        if j_target.apc_usd is None:
                            j_target.apc_usd = oa_j.apc_usd
                        if not j_target.homepage_url:
                            j_target.homepage_url = oa_j.homepage_url
                        for top in oa_j.topics:
                            if top not in j_target.topics:
                                j_target.topics.append(top)
                        if "openalex" not in j_target.source_providers:
                            j_target.source_providers.append("openalex")

            if open_access_only:
                merged = [j for j in merged if j.is_oa or j.is_in_doaj]

            # Optional Elsevier Serial Title CiteScore / SJR / SNIP enrichment
            if self.elsevier_api_key:
                for j in merged[:limit]:
                    target_issn = j.issn_l or (j.issns[0] if j.issns else None)
                    if target_issn:
                        els_metrics = await enrich_journal_elsevier_serial(
                            client, target_issn, api_key=self.elsevier_api_key
                        )
                        if els_metrics:
                            j.metrics.citescore = els_metrics.citescore
                            j.metrics.sjr = els_metrics.sjr
                            j.metrics.snip = els_metrics.snip
                            if "elsevier_scopus" not in j.source_providers:
                                j.source_providers.append("elsevier_scopus")

            # Optional Clarivate Web of Science JCR (JIF, JCI, Quartile) enrichment
            if self.wos_api_key:
                for j in merged[:limit]:
                    target_issn = j.issn_l or (j.issns[0] if j.issns else None)
                    if target_issn:
                        wos_metrics = await enrich_journal_wos_jcr(
                            client, target_issn, api_key=self.wos_api_key
                        )
                        if wos_metrics:
                            j.metrics.jif = wos_metrics.jif
                            j.metrics.jci = wos_metrics.jci
                            j.metrics.jif_quartile = wos_metrics.jif_quartile
                            j.metrics.jif_percentile = wos_metrics.jif_percentile
                            if "clarivate_wos" not in j.source_providers:
                                j.source_providers.append("clarivate_wos")

        final = merged[:limit]
        return SearchJournalsResponse(
            query=query or issn or "*",
            total_returned=len(final),
            providers_queried=list(tasks.keys()),
            results=final,
            warnings=warnings,
        )

    async def aget_paper(
        self,
        identifier: str,
        include_bibtex: bool = True,
        enrich_oa: bool = True,
    ) -> Optional[PaperRecord]:
        id_type, norm_val = classify_identifier(identifier)

        async with httpx.AsyncClient(headers=self._headers, timeout=self.timeout) as client:
            candidates: List[PaperRecord] = []

            if id_type == "doi":
                results = await asyncio.gather(
                    get_work_openalex(client, norm_val, "doi", self.openalex_api_key, self.mailto),
                    get_paper_s2(client, norm_val, "doi", self.s2_api_key),
                    get_work_crossref(client, norm_val, self.mailto),
                    get_paper_europe_pmc(client, norm_val, "doi"),
                    return_exceptions=True,
                )
                for r in results:
                    if isinstance(r, PaperRecord):
                        candidates.append(r)

            elif id_type == "arxiv":
                results = await asyncio.gather(
                    get_arxiv_paper(client, norm_val),
                    get_work_openalex(client, norm_val, "arxiv", self.openalex_api_key, self.mailto),
                    get_paper_s2(client, norm_val, "arxiv", self.s2_api_key),
                    return_exceptions=True,
                )
                for r in results:
                    if isinstance(r, PaperRecord):
                        candidates.append(r)
                doi = next((c.doi for c in candidates if c.doi and not c.doi.startswith("10.48550/arxiv.")), None)
                if doi:
                    oa_w = await get_work_openalex(client, doi, "doi", self.openalex_api_key, self.mailto)
                    if oa_w:
                        candidates.append(oa_w)

            elif id_type in ("pmid", "pmcid"):
                results = await asyncio.gather(
                    get_paper_europe_pmc(client, norm_val, id_type),
                    get_work_openalex(client, norm_val, id_type, self.openalex_api_key, self.mailto),
                    get_paper_s2(client, norm_val, id_type, self.s2_api_key),
                    return_exceptions=True,
                )
                for r in results:
                    if isinstance(r, PaperRecord):
                        candidates.append(r)

            elif id_type == "openalex_work":
                oa_w = await get_work_openalex(client, norm_val, "openalex_work", self.openalex_api_key, self.mailto)
                if oa_w:
                    candidates.append(oa_w)
                    if oa_w.doi:
                        s2_w = await get_paper_s2(client, oa_w.doi, "doi", self.s2_api_key)
                        if s2_w:
                            candidates.append(s2_w)

            else:
                search_res = await self.asearch_papers(identifier, limit=1, include_bibtex=include_bibtex)
                if search_res.results:
                    candidates.append(search_res.results[0])

            if not candidates:
                return None

            merged = candidates[0]
            for c in candidates[1:]:
                merged = merge_two_papers(merged, c)

            if enrich_oa and merged.doi and not merged.pdf_url:
                try:
                    upw = await resolve_unpaywall_oa(client, merged.doi, email=self.mailto)
                    if upw.get("pdf_url"):
                        merged.pdf_url = upw["pdf_url"]
                        merged.is_oa = True
                        merged.oa_status = merged.oa_status or upw.get("oa_status")
                        if "unpaywall" not in merged.source_providers:
                            merged.source_providers.append("unpaywall")
                except Exception:
                    pass

            if include_bibtex:
                bib = await self._resolve_best_bibtex(client, merged)
                merged.bibtex = bib

            return merged

    async def _resolve_best_bibtex(self, client: httpx.AsyncClient, paper: PaperRecord) -> str:
        if paper.doi:
            try:
                doi_bib = await fetch_doi_bibtex(client, paper.doi)
                if doi_bib:
                    return doi_bib
            except Exception:
                pass
        if paper.arxiv_id:
            try:
                arx_bib = await fetch_arxiv_bibtex(client, paper.arxiv_id)
                if arx_bib:
                    return arx_bib
            except Exception:
                pass
        if paper.dblp_key:
            try:
                dblp_bib = await fetch_dblp_bibtex(client, paper.dblp_key)
                if dblp_bib:
                    return dblp_bib
            except Exception:
                pass
        if paper.inspire_id:
            try:
                insp_bib = await fetch_inspire_bibtex(client, paper.inspire_id)
                if insp_bib:
                    return insp_bib
            except Exception:
                pass
        return synthesize_bibtex(paper)

    async def aget_bibtex(self, identifier_or_query: str) -> str:
        id_type, norm_val = classify_identifier(identifier_or_query)
        async with httpx.AsyncClient(headers=self._headers, timeout=self.timeout) as client:
            if id_type == "doi":
                bib = await fetch_doi_bibtex(client, norm_val)
                if bib:
                    return bib
            elif id_type == "arxiv":
                bib = await fetch_arxiv_bibtex(client, norm_val)
                if bib:
                    return bib
            elif id_type == "dblp":
                bib = await fetch_dblp_bibtex(client, norm_val)
                if bib:
                    return bib

        paper = await self.aget_paper(identifier_or_query, include_bibtex=True)
        if not paper:
            raise ValueError(f"Could not resolve paper for BibTeX: {identifier_or_query}")
        return paper.bibtex or synthesize_bibtex(paper)

    async def aget_pdf_context(
        self,
        identifier_or_query: str,
        focus_query: Optional[str] = None,
        max_chars: int = 12000,
    ) -> PaperContextResult:
        paper = await self.aget_paper(identifier_or_query, include_bibtex=True, enrich_oa=True)
        if not paper:
            raise ValueError(f"Paper not found for context extraction: {identifier_or_query}")

        sections: List[Dict[str, str]] = []
        snippets: List[ContextSnippet] = []
        excerpts: List[str] = []
        sources: List[str] = list(paper.source_providers)

        async with httpx.AsyncClient(headers=self._headers, timeout=self.timeout) as client:
            # Tier 1: Semantic Scholar 500-word full-text snippet search
            s2_query = focus_query or paper.title
            s2_paper_ids = [paper.semantic_scholar_id] if paper.semantic_scholar_id else None
            try:
                s2_snips = await search_snippets_s2(
                    client,
                    query=s2_query,
                    paper_ids=s2_paper_ids,
                    limit=6,
                    api_key=self.s2_api_key,
                )
                if s2_snips:
                    snippets.extend(s2_snips)
                    if "semantic_scholar_snippet" not in sources:
                        sources.append("semantic_scholar_snippet")
            except Exception:
                pass

            # Tier 2: arXiv HTML / ar5iv LaTeXML full-text section extraction
            if paper.arxiv_id:
                arx_secs, arx_snips, arx_excerpt = await extract_arxiv_html_context(
                    client,
                    arxiv_id=paper.arxiv_id,
                    focus_query=focus_query,
                    max_chars=max_chars,
                )
                if arx_secs:
                    sections.extend(arx_secs)
                if arx_snips:
                    snippets.extend(arx_snips)
                if arx_excerpt:
                    excerpts.append(arx_excerpt)
                    sources.append("arxiv_html_fulltext")

            # Tier 3: NCBI PMC BioC JSON / PubTator 3.0 full-text section extraction
            if paper.pmcid or paper.pmid:
                bioc_secs, bioc_snips, bioc_excerpt = await extract_pmc_bioc_context(
                    client,
                    pmcid=paper.pmcid,
                    pmid=paper.pmid,
                    focus_query=focus_query,
                    max_chars=max_chars,
                )
                if bioc_secs:
                    sections.extend(bioc_secs)
                if bioc_snips:
                    snippets.extend(bioc_snips)
                if bioc_excerpt:
                    excerpts.append(bioc_excerpt)
                    sources.append("ncbi_pmc_bioc_json")

            # Tier 3.5: Publisher TDM Full-Text APIs (Wiley TDM PDF, Elsevier ScienceDirect XML/JSON, Springer Nature JATS XML)
            if paper.doi and len(sections) <= 2:
                if self.wiley_tdm_token and (paper.doi.startswith("10.1002/") or paper.doi.startswith("10.1111/")):
                    w_secs, w_snips, w_exc = await extract_wiley_tdm_pdf_context(
                        client, paper.doi, focus_query=focus_query, max_chars=max_chars, tdm_token=self.wiley_tdm_token
                    )
                    if w_secs:
                        sections.extend(w_secs)
                        snippets.extend(w_snips)
                        if w_exc:
                            excerpts.append(w_exc)
                        sources.append("wiley_tdm_pdf_api")

                if self.elsevier_api_key and paper.doi.startswith("10.1016/"):
                    sd_secs, sd_snips, sd_exc = await extract_sciencedirect_fulltext(
                        client, paper.doi, focus_query=focus_query, max_chars=max_chars, api_key=self.elsevier_api_key
                    )
                    if sd_secs:
                        sections.extend(sd_secs)
                        snippets.extend(sd_snips)
                        if sd_exc:
                            excerpts.append(sd_exc)
                        sources.append("elsevier_sciencedirect_api")

                if self.springer_api_key and (paper.doi.startswith("10.1038/") or paper.doi.startswith("10.1007/")):
                    sp_secs, sp_snips, sp_exc = await extract_springer_jats_context(
                        client, paper.doi, focus_query=focus_query, max_chars=max_chars, api_key=self.springer_api_key
                    )
                    if sp_secs:
                        sections.extend(sp_secs)
                        snippets.extend(sp_snips)
                        if sp_exc:
                            excerpts.append(sp_exc)
                        sources.append("springer_jats_xml")

            # Tier 4: Direct Open Access PDF extraction via pypdf
            if len(sections) <= 2 and paper.pdf_url:
                pdf_secs, pdf_snips, pdf_excerpt = await extract_pdf_text_context(
                    client,
                    pdf_url=paper.pdf_url,
                    focus_query=focus_query,
                    max_chars=max_chars,
                )
                if pdf_secs:
                    sections.extend(pdf_secs)
                if pdf_snips:
                    snippets.extend(pdf_snips)
                if pdf_excerpt:
                    excerpts.append(pdf_excerpt)
                    sources.append("open_access_pdf_pypdf")

        if not excerpts:
            parts: List[str] = []
            if paper.abstract:
                parts.append(f"### Abstract\n{paper.abstract}")
            if paper.tldr:
                parts.append(f"### AI TLDR\n{paper.tldr}")
            for sn in snippets[:5]:
                parts.append(f"### Snippet ({sn.section or sn.source})\n{sn.text}")
            excerpts.append("\n\n".join(parts)[:max_chars])

        return PaperContextResult(
            identifier=identifier_or_query,
            title=paper.title,
            doi=paper.doi,
            arxiv_id=paper.arxiv_id,
            pmid=paper.pmid,
            pmcid=paper.pmcid,
            abstract=paper.abstract,
            tldr=paper.tldr,
            pdf_url=paper.pdf_url,
            html_url=paper.html_url,
            bibtex=paper.bibtex,
            sections=sections[:12],
            snippets=snippets[:10],
            full_text_excerpt="\n\n".join(excerpts)[:max_chars],
            extraction_sources=list(dict.fromkeys(sources)),
        )

    async def aget_citations(
        self,
        identifier: str,
        direction: str = "both",
        limit: int = 15,
    ) -> CitationGraphResult:
        paper = await self.aget_paper(identifier, include_bibtex=False, enrich_oa=False)
        target_id = paper.openalex_id or paper.doi or identifier if paper else identifier
        doi = paper.doi if paper else clean_doi(identifier)

        citing = []
        refs = []
        used_provs: List[str] = []

        async with httpx.AsyncClient(headers=self._headers, timeout=self.timeout) as client:
            if paper and (paper.openalex_id or paper.doi):
                oa_cit = await get_citations_openalex(
                    client,
                    openalex_id_or_doi=paper.openalex_id or paper.doi or target_id,
                    direction=direction,
                    limit=limit,
                    api_key=self.openalex_api_key,
                    mailto=self.mailto,
                )
                citing.extend(oa_cit.get("citing") or [])
                refs.extend(oa_cit.get("references") or [])
                if citing or refs:
                    used_provs.append("openalex")

            if doi and (len(citing) < limit or len(refs) < limit):
                oc_cit = await get_opencitations(client, doi=doi, direction=direction, limit=limit)
                if not citing and oc_cit.get("citing"):
                    citing.extend(oc_cit["citing"])
                    used_provs.append("opencitations")
                if not refs and oc_cit.get("references"):
                    refs.extend(oc_cit["references"])
                    if "opencitations" not in used_provs:
                        used_provs.append("opencitations")

        return CitationGraphResult(
            identifier=identifier,
            citation_count=paper.citation_count if paper else len(citing),
            reference_count=paper.reference_count if paper else len(refs),
            citing_papers=citing[:limit],
            references=refs[:limit],
            source_providers=used_provs,
        )

    def search_papers(self, *args: Any, **kwargs: Any) -> SearchPapersResponse:
        return asyncio.run(self.asearch_papers(*args, **kwargs))

    def search_journals(self, *args: Any, **kwargs: Any) -> SearchJournalsResponse:
        return asyncio.run(self.asearch_journals(*args, **kwargs))

    def get_paper(self, *args: Any, **kwargs: Any) -> Optional[PaperRecord]:
        return asyncio.run(self.aget_paper(*args, **kwargs))

    def get_bibtex(self, *args: Any, **kwargs: Any) -> str:
        return asyncio.run(self.aget_bibtex(*args, **kwargs))

    def get_pdf_context(self, *args: Any, **kwargs: Any) -> PaperContextResult:
        return asyncio.run(self.aget_pdf_context(*args, **kwargs))

    def get_citations(self, *args: Any, **kwargs: Any) -> CitationGraphResult:
        return asyncio.run(self.aget_citations(*args, **kwargs))
