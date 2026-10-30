---
name: academic-search
description: Search academic papers, preprints, and journals across 36+ scholarly databases and publishers (OpenAlex, Semantic Scholar, Crossref, Clarivate Web of Science Starter/Expanded/JCR, Elsevier Scopus/ScienceDirect/Serial Title, Wiley Online Library TDM API, Springer Nature Meta v2/OA JATS/TDM, IEEE Xplore, Taylor & Francis, SAGE, Oxford University Press, Cambridge University Press, ACM, ACS, APS, IOP, RSC, MDPI, Frontiers, PLOS, arXiv, PubMed/Europe PMC, PMC BioC, PubTator 3.0, DOAJ, DBLP, INSPIRE-HEP, NASA ADS, OpenCitations, DataCite, OpenAIRE, Unpaywall, CORE, bioRxiv/medRxiv, HAL, Zenodo, Dimensions, The Lens, Consensus, scite, Elicit, FutureHouse PaperQA2). Retrieve normalized metadata, journal impact metrics (2-year mean citedness, h-index, CiteScore, SJR, SNIP, JCR Impact Factor JIF & Quartiles Q1-Q4), canonical BibTeX/CSL-JSON citations, reconstructed abstracts, citation graphs, and full-text PDF/HTML/XML section context.
---

# Academic Search Database Skill (MCP, CLI, SDK & Direct REST APIs)

Use this skill whenever an agent needs to:
1. **Search academic papers or preprints** by topic, title, author, DOI, arXiv ID, PMID/PMCID, year range, journal/venue, or citation count.
2. **Search academic journals or conferences** and retrieve ISSNs, Open Access / DOAJ status, APC fees, and impact metrics (`2yr_mean_citedness`, `h_index`, `i10_index`, `CiteScore`, `SJR`, `SNIP`, `JIF`).
3. **Export verified BibTeX or CSL-JSON** citations without hallucinated fields or broken LaTeX keys.
4. **Extract full-text PDF, HTML, or BioC JSON context** (Introduction, Methods, Results, Discussion, equations, tables, and 500-word body snippets) along with complete reconstructed abstracts.
5. **Traverse citation graphs** (forward citing papers, backward references, and supporting/contrasting Smart Citations).

---

## Quick Decision Tree: Which Interface Should the Agent Use?

| Agent Environment | Recommended Interface | Command / Entry Point |
|---|---|---|
| **MCP-enabled agent** (Claude Code, Cursor, Codex, Desktop) | **Unified MCP Server** (`acadsearch-mcp`) | Tools: `academic_search_papers`, `academic_search_journals`, `academic_get_paper`, `academic_get_bibtex`, `academic_get_pdf_context`, `academic_get_citations`, `academic_list_databases` |
| **Bash / CLI-enabled agent** | **`acadsearch` CLI** | `acadsearch papers "<query>"`, `acadsearch journals "<query>"`, `acadsearch paper "<id>"`, `acadsearch bibtex "<id>"`, `acadsearch context "<id>" --query "<focus>"` |
| **Python code / notebook execution** | **`acadsearch` Python SDK** | `from acadsearch import AcademicSearchClient; client = AcademicSearchClient()` |
| **HTTP microservice / multi-language agent** | **FastAPI REST Server** (`openapi.json`) | `acadsearch serve --port 8000` -> `GET /v1/papers/search`, `GET /v1/journals/search`, `GET /v1/bibtex`, `GET /v1/context` |
| **Zero-install sandbox (`curl` only)** | **Direct REST API calls** | Load the relevant reference file below for exact `curl` endpoints, query syntax, and rate limits. |

---

## Reference Manual Routing Table

Load the matching reference file when calling upstream academic APIs directly or debugging provider-specific parameters:

| Reference File | Covered Databases & Workflows | When to Read |
|---|---|---|
| `references/open-scholarly-graphs.md` | **OpenAlex**, **Semantic Scholar**, **Crossref**, **OpenCitations**, **DataCite**, **OpenAIRE**, **ORCID** | Global paper search, OpenAlex inverted-index abstract reconstruction, singleton `$0.00` lookups, citation graphs, SPECTER2 embeddings |
| `references/journals-oa-bibtex.md` | **DOAJ v4**, **Unpaywall v2**, **DOI Content Negotiation (`doi.org`)**, **OpenAlex `/sources`**, **CORE v3**, **HAL**, **Zenodo** | Journal metrics (`2yr_mean_citedness`, `h_index`, APCs), ISSN resolution, universal BibTeX/CSL-JSON negotiation, legal OA PDF lookup |
| `references/discipline-databases.md` | **arXiv + ar5iv/HTML**, **PubMed (NCBI E-utilities)**, **Europe PMC**, **NCBI PMC BioC JSON**, **PubTator 3.0**, **bioRxiv/medRxiv**, **DBLP**, **INSPIRE-HEP**, **NASA ADS**, **ACL / HF Papers** | CS/ML/Math/Physics (`arXiv`, `DBLP`, `INSPIRE`, `ADS`) and Biomedical (`PubMed`, `Europe PMC`, `BioC`, `PubTator3`, `bioRxiv`) queries |
| `references/publisher-and-ai-apis.md` | **Clarivate Web of Science (Starter v1, Expanded, JCR Journals v1)**, **Elsevier (Scopus Search, Abstract Retrieval, ScienceDirect Full-Text, Serial Title CiteScore/SJR/SNIP)**, **Wiley Online Library TDM API v1 (`wiley`)**, **Springer Nature (Meta v2, OA JATS, Full-Text TDM)**, **IEEE Xplore**, **16 Major Publishers (`taylor_francis`, `oup`, `sage`, `cup`, `acm`, `acs`, `aps`, `iop`, `rsc`, `mdpi`, `frontiers`, `plos`)**, **Dimensions DSL v2**, **The Lens**, **Google Scholar**, **Consensus MCP**, **scite MCP**, **Elicit v2**, **FutureHouse PaperQA2** | Commercial publisher APIs, zero-key Crossref Member publisher search, CiteScore/SJR/JCR Impact Factor (JIF) quartiles, Wiley/ScienceDirect/Springer full-text TDM, and Smart Citation verification |
| `references/fulltext-pdf-context.md` | **4-Tier Full-Text & PDF Context Pipeline** (`Semantic Scholar Snippets` -> `arXiv HTML / ar5iv` -> `PMC BioC JSON` -> `OA PDF pypdf / Jina Reader / GROBID`) | Extracting Methods, Results, equations, and tables from papers without blowing up the LLM context window |

---

## Core Workflows with `acadsearch`

### 1. Search Papers + Metadata + Abstract + BibTeX
```bash
# JSON output for programmatic agent parsing
acadsearch papers "Retrieval-Augmented Generation" --year-min 2023 --limit 5 --sort citations --format json

# Markdown summary with inline BibTeX blocks
acadsearch papers "Attention Is All You Need" --limit 3 --format markdown

# Direct BibTeX batch output for .bib files
acadsearch papers "Gaussian Splatting" --limit 5 --format bibtex >> references.bib

# Search specific commercial publishers (Wiley, Scopus/Elsevier, Springer Nature, IEEE, OUP, Taylor & Francis, ACM, ACS, APS)
acadsearch papers "solid state lithium battery" --providers wiley,scopus,springer_nature,ieee,acs --limit 5 --format markdown
```

### 2. Search Journals & Retrieve Impact Metrics
```bash
# Search journal by title (returns ISSN, 2yr_mean_citedness IF proxy, h-index, i10-index, OA/DOAJ status, APC USD)
acadsearch journals "Nature Machine Intelligence" --limit 3 --format markdown

# Lookup journal by exact ISSN
acadsearch journals --issn "1476-4687" --format json

# Search Open Access / DOAJ journals only
acadsearch journals "Bioinformatics" --oa --limit 5 --format markdown
```

### 3. Resolve Official or Synthesized BibTeX for Any Identifier
```bash
# Works with DOIs, arXiv IDs, DBLP keys, PMIDs, or paper titles
acadsearch bibtex "10.1038/nature14539"
acadsearch bibtex "arXiv:1706.03762"
acadsearch bibtex "conf/nips/VaswaniSPUJGKP17"
```

### 4. Extract Full-Text & PDF Context (Sections, Equations, Snippets & Abstract)
```bash
# Extract arXiv LaTeXML HTML sections & targeted snippets
acadsearch context "arXiv:2402.01680" --query "multi-agent communication architecture" --max-chars 10000 --format markdown

# Extract biomedical PMC BioC JSON sections (INTRO, METHODS, RESULTS, DISCUSS, TABLE, FIG)
acadsearch context "PMID:29355051" --query "doxorubicin antitumor immunotoxicity" --format markdown
```

### 5. Python SDK Quickstart
```python
from acadsearch import AcademicSearchClient

client = AcademicSearchClient(mailto="agent@yourdomain.org")

# 1. Multi-provider deduplicated paper search
papers = client.search_papers("Vision Transformer", year_min=2020, limit=5, sort="citations")
for p in papers.results:
    print(p.title, p.year, p.doi, p.citation_count, p.pdf_url)
    print(p.abstract)
    print(p.bibtex)

# 2. Journal lookup with OpenAlex + DOAJ + Crossref metrics
journals = client.search_journals("Journal of Machine Learning Research", limit=2)
for j in journals.results:
    print(j.title, j.issns, j.metrics.two_year_mean_citedness, j.metrics.h_index, j.is_in_doaj)

# 3. Full-text & PDF context extraction
ctx = client.get_pdf_context("arXiv:1706.03762", focus_query="scaled dot-product attention matrix")
print(ctx.full_text_excerpt)
```

---

## Critical Guardrails for Academic Agents

1. **Never Hallucinate DOIs or BibTeX Keys**: Always verify a paper via `acadsearch paper "<title_or_doi>"` or `https://doi.org/{doi}` with `Accept: application/x-bibtex` before writing a citation into a manuscript or `.bib` file.
2. **Use Singleton Lookups on OpenAlex When Keyless Quota Is Tight**: OpenAlex's `/works?search=...` endpoint costs `$0.001` against the shared IP keyless budget (`$0.10/day`), whereas singleton lookups (`GET /works/https://doi.org/{doi}`, `GET /works/https://doi.org/10.48550/arXiv.{id}`, and `GET /sources/issn:{issn}`) cost **`$0.0000` (100% free)**! `acadsearch` automatically uses this zero-cost singleton enrichment fallback.
3. **Unpaywall `/v2/search` Retirement**: Unpaywall permanently retired `GET /v2/search` on **September 18, 2026** (`HTTP 410 Gone`). Use `GET https://api.unpaywall.org/v2/{doi}?email=YOUR_EMAIL` for OA PDF resolution and OpenAlex `/works?search=...&filter=is_oa:true` for text search.
4. **DBLP Anubis v1.27.0 Bot Challenge (HTTP 202)**: In 2026, `dblp.org` protects `/search/publ/api`, `/search/venue/api`, and `/rec/{key}.bib` with an Anubis `metarefresh` challenge (`HTTP 202`). `acadsearch` automatically solves the 1.08s `pass-challenge` handshake and caches the `dblp_org-auth` cookie.
5. **Respect arXiv Rate Limits**: `export.arxiv.org/api/query` enforces **1 request every 3 seconds (0.33 RPS)** and a single concurrent connection. Prefer HTML full text (`https://arxiv.org/html/{id}` or `https://ar5iv.labs.arxiv.org/html/{id}`) over raw PDF downloads whenever available.
