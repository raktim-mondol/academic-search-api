from __future__ import annotations
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from .client import AcademicSearchClient
from .mcp_server import handle_jsonrpc_message
from .models import (
    CitationGraphResult,
    PaperContextResult,
    PaperRecord,
    SearchJournalsResponse,
    SearchPapersResponse,
)

app = FastAPI(
    title="Unified Academic Search Database API",
    version="1.0.0",
    description=(
        "Agent-ready REST & Model Context Protocol (MCP) API aggregating OpenAlex, Semantic Scholar, "
        "Crossref, arXiv, PubMed/Europe PMC, PMC BioC, PubTator 3.0, DOAJ, DBLP, INSPIRE-HEP, Unpaywall, "
        "OpenCitations, and commercial academic databases for paper search, journal metrics, BibTeX, "
        "abstract reconstruction, and full-text PDF context extraction."
    ),
)

client = AcademicSearchClient()


class PaperSearchRequest(BaseModel):
    query: str
    providers: Optional[List[str]] = None
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    open_access_only: bool = False
    venue: Optional[str] = None
    min_citations: Optional[int] = None
    limit: int = 10
    sort: Optional[str] = "relevance"
    include_bibtex: bool = True


@app.get("/health", tags=["System"])
async def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "acadsearch-api", "version": "1.0.0"}


@app.get("/v1/databases", tags=["System"])
async def list_databases() -> Dict[str, Any]:
    dbs = client.list_databases()
    return {"count": len(dbs), "databases": dbs}


@app.get("/v1/papers/search", response_model=SearchPapersResponse, tags=["Papers"])
async def search_papers_get(
    q: str = Query(..., description="Search query for academic papers"),
    providers: Optional[str] = Query(None, description="Comma-separated provider IDs (e.g. openalex,semantic_scholar,arxiv)"),
    year_min: Optional[int] = Query(None, description="Minimum publication year"),
    year_max: Optional[int] = Query(None, description="Maximum publication year"),
    open_access_only: bool = Query(False, description="Only return Open Access papers"),
    venue: Optional[str] = Query(None, description="Journal name, conference acronym, or ISSN"),
    min_citations: Optional[int] = Query(None, description="Minimum citation count"),
    limit: int = Query(10, ge=1, le=50),
    sort: Optional[str] = Query("relevance", description="relevance | citations | year"),
    include_bibtex: bool = Query(True, description="Include BibTeX citation string"),
) -> SearchPapersResponse:
    prov_list = [p.strip() for p in providers.split(",") if p.strip()] if providers else None
    return await client.asearch_papers(
        query=q,
        providers=prov_list,
        year_min=year_min,
        year_max=year_max,
        open_access_only=open_access_only,
        venue=venue,
        min_citations=min_citations,
        limit=limit,
        sort=sort,
        include_bibtex=include_bibtex,
    )


@app.post("/v1/papers/search", response_model=SearchPapersResponse, tags=["Papers"])
async def search_papers_post(body: PaperSearchRequest) -> SearchPapersResponse:
    return await client.asearch_papers(
        query=body.query,
        providers=body.providers,
        year_min=body.year_min,
        year_max=body.year_max,
        open_access_only=body.open_access_only,
        venue=body.venue,
        min_citations=body.min_citations,
        limit=body.limit,
        sort=body.sort,
        include_bibtex=body.include_bibtex,
    )


@app.get("/v1/papers/lookup", response_model=PaperRecord, tags=["Papers"])
async def lookup_paper(
    id: str = Query(..., description="DOI, arXiv ID, PMID, PMCID, OpenAlex ID, or paper title"),
    include_bibtex: bool = Query(True),
) -> PaperRecord:
    paper = await client.aget_paper(identifier=id, include_bibtex=include_bibtex)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper not found for identifier: {id}")
    return paper


@app.get("/v1/journals/search", response_model=SearchJournalsResponse, tags=["Journals"])
async def search_journals_get(
    q: Optional[str] = Query(None, description="Journal title or subject query"),
    issn: Optional[str] = Query(None, description="ISSN (e.g. 1476-4687)"),
    open_access_only: bool = Query(False, description="Only return Open Access / DOAJ journals"),
    providers: Optional[str] = Query(None, description="Comma-separated providers (openalex,doaj,crossref,dblp)"),
    limit: int = Query(10, ge=1, le=50),
) -> SearchJournalsResponse:
    prov_list = [p.strip() for p in providers.split(",") if p.strip()] if providers else None
    return await client.asearch_journals(
        query=q,
        issn=issn,
        open_access_only=open_access_only,
        providers=prov_list,
        limit=limit,
    )


@app.get("/v1/bibtex", response_class=PlainTextResponse, tags=["BibTeX & Context"])
async def get_bibtex_endpoint(
    id: str = Query(..., description="DOI, arXiv ID, DBLP key, PMID, or paper title"),
) -> str:
    try:
        return await client.aget_bibtex(id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/v1/context", response_model=PaperContextResult, tags=["BibTeX & Context"])
async def get_pdf_context_endpoint(
    id: str = Query(..., description="DOI, arXiv ID, PMCID, PMID, or paper title"),
    focus_query: Optional[str] = Query(None, description="Specific method, claim, or question to rank full-text snippets"),
    max_chars: int = Query(12000, ge=500, le=50000),
) -> PaperContextResult:
    try:
        return await client.aget_pdf_context(
            identifier_or_query=id,
            focus_query=focus_query,
            max_chars=max_chars,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/v1/citations", response_model=CitationGraphResult, tags=["Citations"])
async def get_citations_endpoint(
    id: str = Query(..., description="DOI, OpenAlex ID, or arXiv ID"),
    direction: str = Query("both", description="both | citing | references"),
    limit: int = Query(15, ge=1, le=50),
) -> CitationGraphResult:
    return await client.aget_citations(identifier=id, direction=direction, limit=limit)


@app.post("/mcp", tags=["Model Context Protocol (MCP)"])
async def mcp_http_endpoint(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Streamable HTTP JSON-RPC 2.0 endpoint for Model Context Protocol (MCP) clients."""
    resp = await handle_jsonrpc_message(client, payload)
    return resp or {"jsonrpc": "2.0", "result": {}}
