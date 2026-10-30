from __future__ import annotations
import argparse
import asyncio
import json
import sys
from typing import Any, List
import uvicorn
from .client import AcademicSearchClient
from .mcp_server import run_stdio_mcp_server


def _format_papers_markdown(res: Any) -> str:
    lines: List[str] = [
        f"# Academic Paper Search Results for: `{res.query}`",
        f"- **Returned**: {res.total_returned} papers | **Providers**: {', '.join(res.providers_queried)}",
        "",
    ]
    for idx, p in enumerate(res.results, 1):
        authors_str = ", ".join(a.name for a in p.authors[:5])
        if len(p.authors) > 5:
            authors_str += " et al."
        venue_str = p.journal.name if p.journal and p.journal.name else (p.publication_type or "Unknown Venue")
        lines.append(f"## {idx}. {p.title} ({p.year or 'n.d.'})")
        lines.append(f"- **Authors**: {authors_str or 'Unknown'}")
        lines.append(f"- **Journal / Venue**: {venue_str} | **Citations**: {p.citation_count if p.citation_count is not None else 'N/A'} | **OA**: {p.is_oa}")
        ids = []
        if p.doi:
            ids.append(f"DOI: `{p.doi}`")
        if p.arxiv_id:
            ids.append(f"arXiv: `{p.arxiv_id}`")
        if p.pmid:
            ids.append(f"PMID: `{p.pmid}`")
        if p.openalex_id:
            ids.append(f"OpenAlex: `{p.openalex_id}`")
        lines.append(f"- **Identifiers**: {' | '.join(ids) if ids else p.id}")
        if p.pdf_url:
            lines.append(f"- **Open Access PDF**: {p.pdf_url}")
        if p.tldr:
            lines.append(f"- **TLDR**: {p.tldr}")
        if p.abstract:
            lines.append(f"- **Abstract**: {p.abstract[:600]}{'...' if len(p.abstract) > 600 else ''}")
        if p.bibtex:
            lines.append("```bibtex\n" + p.bibtex + "\n```")
        lines.append("")
    return "\n".join(lines)


def _format_journals_markdown(res: Any) -> str:
    lines: List[str] = [
        f"# Academic Journal Search Results for: `{res.query}`",
        f"- **Returned**: {res.total_returned} journals | **Providers**: {', '.join(res.providers_queried)}",
        "",
    ]
    for idx, j in enumerate(res.results, 1):
        m = j.metrics
        lines.append(f"## {idx}. {j.title}")
        lines.append(f"- **ISSNs**: {', '.join(j.issns) if j.issns else 'N/A'} | **Publisher**: {j.publisher or 'N/A'}")
        lines.append(
            f"- **Open Access**: {j.is_oa} | **In DOAJ**: {j.is_in_doaj} | **APC (USD)**: {j.apc_usd if j.apc_usd is not None else 'N/A'}"
        )
        lines.append(
            f"- **Impact Metrics**: 2yr Mean Citedness (IF proxy): `{m.two_year_mean_citedness or 'N/A'}` | "
            f"h-index: `{m.h_index or 'N/A'}` | i10-index: `{m.i10_index or 'N/A'}` | Works: `{m.works_count or 'N/A'}`"
        )
        if j.topics:
            lines.append(f"- **Topics**: {', '.join(j.topics[:6])}")
        if j.homepage_url:
            lines.append(f"- **Homepage**: {j.homepage_url}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="acadsearch",
        description="Unified Academic Search CLI, REST API, and MCP Server for AI Agents.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # 1. papers
    p_papers = sub.add_parser("papers", help="Search academic papers and preprints")
    p_papers.add_argument("query", help="Search query string")
    p_papers.add_argument("--providers", help="Comma-separated list of providers")
    p_papers.add_argument("--year-min", type=int, help="Minimum publication year")
    p_papers.add_argument("--year-max", type=int, help="Maximum publication year")
    p_papers.add_argument("--oa", action="store_true", help="Open Access papers only")
    p_papers.add_argument("--venue", help="Filter by journal name, acronym, or ISSN")
    p_papers.add_argument("--min-citations", type=int, help="Minimum citation count")
    p_papers.add_argument("--limit", type=int, default=5, help="Max results (default 5)")
    p_papers.add_argument("--sort", choices=["relevance", "citations", "year"], default="relevance")
    p_papers.add_argument("--format", choices=["json", "markdown", "bibtex"], default="json")

    # 2. journals
    p_journals = sub.add_parser("journals", help="Search academic journals and venues with impact metrics")
    p_journals.add_argument("query", nargs="?", default=None, help="Journal title or field query")
    p_journals.add_argument("--issn", help="ISSN (e.g. 1476-4687)")
    p_journals.add_argument("--oa", action="store_true", help="Open Access / DOAJ journals only")
    p_journals.add_argument("--providers", help="Comma-separated providers (openalex,doaj,crossref,dblp)")
    p_journals.add_argument("--limit", type=int, default=5, help="Max results (default 5)")
    p_journals.add_argument("--format", choices=["json", "markdown"], default="json")

    # 3. paper
    p_paper = sub.add_parser("paper", help="Lookup a single paper by DOI, arXiv ID, PMID, PMCID, or title")
    p_paper.add_argument("identifier", help="Identifier or title")
    p_paper.add_argument("--format", choices=["json", "markdown", "bibtex"], default="json")

    # 4. bibtex
    p_bib = sub.add_parser("bibtex", help="Fetch or synthesize BibTeX for any paper identifier or title")
    p_bib.add_argument("identifier", help="DOI, arXiv ID, DBLP key, PMID, or paper title")

    # 5. context
    p_ctx = sub.add_parser("context", help="Extract full-text sections, snippets, abstract, and PDF context")
    p_ctx.add_argument("identifier", help="DOI, arXiv ID, PMCID, PMID, or paper title")
    p_ctx.add_argument("--query", help="Optional focus query to rank full-text snippets")
    p_ctx.add_argument("--max-chars", type=int, default=12000, help="Max excerpt chars")
    p_ctx.add_argument("--format", choices=["json", "markdown"], default="json")

    # 6. citations
    p_cit = sub.add_parser("citations", help="Get incoming citations and outgoing references for a paper")
    p_cit.add_argument("identifier", help="DOI, OpenAlex ID, or arXiv ID")
    p_cit.add_argument("--direction", choices=["both", "citing", "references"], default="both")
    p_cit.add_argument("--limit", type=int, default=10)
    p_cit.add_argument("--format", choices=["json", "markdown"], default="json")

    # 7. databases
    sub.add_parser("databases", help="List all supported academic databases and API metadata")

    # 8. serve (HTTP REST + MCP server)
    p_serve = sub.add_parser("serve", help="Run the FastAPI HTTP REST + Streamable MCP server")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=8000)

    # 9. mcp (stdio MCP server)
    sub.add_parser("mcp", help="Run the Model Context Protocol (MCP) stdio server")

    args = parser.parse_args()
    client = AcademicSearchClient()

    if args.cmd == "serve":
        uvicorn.run("acadsearch.server:app", host=args.host, port=args.port, reload=False)
        return

    if args.cmd == "mcp":
        asyncio.run(run_stdio_mcp_server())
        return

    if args.cmd == "databases":
        print(json.dumps(client.list_databases(), indent=2, ensure_ascii=False))
        return

    if args.cmd == "papers":
        provs = [p.strip() for p in args.providers.split(",") if p.strip()] if args.providers else None
        res = client.search_papers(
            query=args.query,
            providers=provs,
            year_min=args.year_min,
            year_max=args.year_max,
            open_access_only=args.oa,
            venue=args.venue,
            min_citations=args.min_citations,
            limit=args.limit,
            sort=args.sort,
            include_bibtex=True,
        )
        if args.format == "json":
            print(json.dumps(res.model_dump(), indent=2, ensure_ascii=False))
        elif args.format == "bibtex":
            print("\n\n".join(p.bibtex for p in res.results if p.bibtex))
        else:
            print(_format_papers_markdown(res))
        return

    if args.cmd == "journals":
        provs = [p.strip() for p in args.providers.split(",") if p.strip()] if args.providers else None
        res = client.search_journals(
            query=args.query,
            issn=args.issn,
            open_access_only=args.oa,
            providers=provs,
            limit=args.limit,
        )
        if args.format == "json":
            print(json.dumps(res.model_dump(), indent=2, ensure_ascii=False))
        else:
            print(_format_journals_markdown(res))
        return

    if args.cmd == "paper":
        paper = client.get_paper(args.identifier, include_bibtex=True)
        if not paper:
            sys.stderr.write(f"Error: Paper not found for {args.identifier}\n")
            sys.exit(1)
        if args.format == "json":
            print(json.dumps(paper.model_dump(), indent=2, ensure_ascii=False))
        elif args.format == "bibtex":
            print(paper.bibtex or "")
        else:
            print(_format_papers_markdown(type("Obj", (), {"query": args.identifier, "total_returned": 1, "providers_queried": paper.source_providers, "results": [paper]})))
        return

    if args.cmd == "bibtex":
        bib = client.get_bibtex(args.identifier)
        print(bib)
        return

    if args.cmd == "context":
        ctx = client.get_pdf_context(args.identifier, focus_query=args.query, max_chars=args.max_chars)
        if args.format == "json":
            print(json.dumps(ctx.model_dump(), indent=2, ensure_ascii=False))
        else:
            print(f"# Full-Text & PDF Context: {ctx.title}\n")
            print(f"- **DOI**: {ctx.doi} | **arXiv**: {ctx.arxiv_id} | **PMID**: {ctx.pmid} | **PMCID**: {ctx.pmcid}")
            print(f"- **PDF URL**: {ctx.pdf_url}\n- **Sources**: {', '.join(ctx.extraction_sources)}\n")
            if ctx.abstract:
                print(f"## Abstract\n{ctx.abstract}\n")
            if ctx.bibtex:
                print(f"## BibTeX\n```bibtex\n{ctx.bibtex}\n```\n")
            if ctx.full_text_excerpt:
                print(f"## Full-Text Excerpt & Sections\n{ctx.full_text_excerpt}\n")
        return

    if args.cmd == "citations":
        cit = client.get_citations(args.identifier, direction=args.direction, limit=args.limit)
        print(json.dumps(cit.model_dump(), indent=2, ensure_ascii=False))
        return


if __name__ == "__main__":
    main()
