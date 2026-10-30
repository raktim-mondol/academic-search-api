from __future__ import annotations
import asyncio
import json
import sys
from typing import Any, Dict, List, Optional
from .client import AcademicSearchClient

MCP_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "academic_search_papers",
        "description": (
            "Search academic papers and preprints across OpenAlex, Semantic Scholar, Crossref, "
            "arXiv, PubMed/Europe PMC, DBLP, DOAJ, INSPIRE-HEP, and CORE. Returns deduplicated "
            "metadata, full reconstructed abstracts, journal metrics, OA PDF URLs, and BibTeX."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (keywords, title, or topic)."},
                "providers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optional subset of databases/publishers: ['openalex', 'semantic_scholar', 'arxiv', "
                        "'pubmed_europepmc', 'crossref', 'dblp', 'doaj', 'inspire_hep', 'core', "
                        "'scopus', 'elsevier', 'sciencedirect', 'wos', 'wiley', 'springer_nature', "
                        "'ieee', 'taylor_francis', 'sage', 'oup', 'cup', 'acm', 'acs', 'aps', 'iop', 'rsc', 'mdpi', 'frontiers', 'plos']."
                    ),
                },
                "year_min": {"type": "integer", "description": "Minimum publication year (e.g. 2020)."},
                "year_max": {"type": "integer", "description": "Maximum publication year (e.g. 2026)."},
                "open_access_only": {"type": "boolean", "default": False, "description": "Filter to Open Access papers with free PDFs."},
                "venue": {"type": "string", "description": "Filter by journal name, conference acronym, or ISSN (XXXX-XXXX)."},
                "min_citations": {"type": "integer", "description": "Minimum citation count."},
                "limit": {"type": "integer", "default": 10, "description": "Max papers to return (1-50)."},
                "sort": {"type": "string", "enum": ["relevance", "citations", "year"], "default": "relevance"},
                "include_bibtex": {"type": "boolean", "default": True, "description": "Include BibTeX entry for each paper."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "academic_search_journals",
        "description": (
            "Search academic journals and conference venues across OpenAlex, DOAJ, Crossref, and DBLP. "
            "Returns ISSNs, publisher, Open Access / DOAJ status, APC fees (USD), h-index, i10-index, "
            "and 2-year mean citedness (open equivalent of 2-year Journal Impact Factor)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Journal title or topic keywords."},
                "issn": {"type": "string", "description": "Exact ISSN lookup (e.g. '1476-4687' for Nature)."},
                "open_access_only": {"type": "boolean", "default": False, "description": "Only return Open Access / DOAJ journals."},
                "limit": {"type": "integer", "default": 10, "description": "Max journals to return (1-50)."},
            },
        },
    },
    {
        "name": "academic_get_paper",
        "description": (
            "Retrieve complete merged metadata, abstract, AI TLDR, Open Access PDF URL, journal info, "
            "and canonical BibTeX for a single paper by DOI (10.xxxx/...), arXiv ID (arXiv:1706.03762), "
            "PMID (37711410), PMCID (PMC11223843), OpenAlex ID (W2741809807), or exact paper title."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "identifier": {"type": "string", "description": "DOI, arXiv ID, PMID, PMCID, OpenAlex ID, or paper title."},
                "include_bibtex": {"type": "boolean", "default": True},
            },
            "required": ["identifier"],
        },
    },
    {
        "name": "academic_get_bibtex",
        "description": (
            "Resolve an official or synthesized BibTeX citation entry for any DOI, arXiv ID, DBLP key, "
            "INSPIRE record, PMID, or paper title via DOI content negotiation, arXiv, DBLP, and Crossref."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "identifier": {"type": "string", "description": "DOI, arXiv ID, DBLP key, PMID, or paper title."},
            },
            "required": ["identifier"],
        },
    },
    {
        "name": "academic_get_pdf_context",
        "description": (
            "Extract full-text sections, equations, tables, and targeted ~500-word body-text passages "
            "from an academic paper without overflowing the agent context window. Cascades through "
            "Semantic Scholar Snippet Search, arXiv HTML / ar5iv LaTeXML, NCBI PMC BioC Full-Text JSON, "
            "and direct Open Access PDF parsing."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "identifier": {"type": "string", "description": "DOI, arXiv ID, PMCID, PMID, or paper title."},
                "focus_query": {
                    "type": "string",
                    "description": "Optional specific question, method, or keyword to rank full-text passages.",
                },
                "max_chars": {
                    "type": "integer",
                    "default": 12000,
                    "description": "Maximum characters of full-text excerpt to return.",
                },
            },
            "required": ["identifier"],
        },
    },
    {
        "name": "academic_get_citations",
        "description": (
            "Traverse the citation graph (incoming citing papers and outgoing references) for a paper "
            "using OpenAlex and OpenCitations Index v2 (COCI)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "identifier": {"type": "string", "description": "DOI, OpenAlex Work ID, or arXiv ID."},
                "direction": {
                    "type": "string",
                    "enum": ["both", "citing", "references"],
                    "default": "both",
                },
                "limit": {"type": "integer", "default": 15},
            },
            "required": ["identifier"],
        },
    },
    {
        "name": "academic_list_databases",
        "description": "List all 24+ supported academic paper and journal databases, rate limits, auth modes, and capabilities.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


async def dispatch_mcp_tool(client: AcademicSearchClient, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name == "academic_search_papers":
        res = await client.asearch_papers(
            query=arguments["query"],
            providers=arguments.get("providers"),
            year_min=arguments.get("year_min"),
            year_max=arguments.get("year_max"),
            open_access_only=bool(arguments.get("open_access_only", False)),
            venue=arguments.get("venue"),
            min_citations=arguments.get("min_citations"),
            limit=int(arguments.get("limit", 10)),
            sort=arguments.get("sort"),
            include_bibtex=bool(arguments.get("include_bibtex", True)),
        )
        return res.model_dump()

    if name == "academic_search_journals":
        res = await client.asearch_journals(
            query=arguments.get("query"),
            issn=arguments.get("issn"),
            open_access_only=bool(arguments.get("open_access_only", False)),
            limit=int(arguments.get("limit", 10)),
        )
        return res.model_dump()

    if name == "academic_get_paper":
        paper = await client.aget_paper(
            identifier=arguments["identifier"],
            include_bibtex=bool(arguments.get("include_bibtex", True)),
        )
        if not paper:
            return {"error": f"No paper found for identifier: {arguments['identifier']}"}
        return paper.model_dump()

    if name == "academic_get_bibtex":
        bib = await client.aget_bibtex(arguments["identifier"])
        return {"identifier": arguments["identifier"], "bibtex": bib}

    if name == "academic_get_pdf_context":
        ctx = await client.aget_pdf_context(
            identifier_or_query=arguments["identifier"],
            focus_query=arguments.get("focus_query"),
            max_chars=int(arguments.get("max_chars", 12000)),
        )
        return ctx.model_dump()

    if name == "academic_get_citations":
        cit = await client.aget_citations(
            identifier=arguments["identifier"],
            direction=arguments.get("direction", "both"),
            limit=int(arguments.get("limit", 15)),
        )
        return cit.model_dump()

    if name == "academic_list_databases":
        return {"databases": client.list_databases()}

    raise ValueError(f"Unknown MCP tool: {name}")


async def handle_jsonrpc_message(client: AcademicSearchClient, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = msg.get("method")
    msg_id = msg.get("id")
    params = msg.get("params") or {}

    if method == "notifications/initialized":
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "acadsearch-mcp-server", "version": "1.0.0"},
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": MCP_TOOLS}}

    if method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments") or {}
        try:
            payload = await dispatch_mcp_tool(client, tool_name, tool_args)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(payload, indent=2, ensure_ascii=False)}],
                    "isError": False,
                },
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error executing {tool_name}: {exc}"}],
                    "isError": True,
                },
            }

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


async def run_stdio_mcp_server() -> None:
    client = AcademicSearchClient()
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        line = await reader.readline()
        if not line:
            break
        raw = line.decode("utf-8", errors="replace").strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue
        resp = await handle_jsonrpc_message(client, msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(run_stdio_mcp_server())
