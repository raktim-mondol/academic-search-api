# Open Global Scholarly Graphs & Identifier Registries

Covers **OpenAlex**, **Semantic Scholar**, **Crossref**, **OpenCitations**, **DataCite**, **OpenAIRE Graph**, and **ORCID**.

---

## 1. OpenAlex (`https://api.openalex.org`)

- **Corpus**: 300M+ core scholarly works (and ~60% more via opt-in `corpus=all`), 250K+ journals/sources, 100M+ authors, 110K+ institutions under **CC0 public domain**.
- **Authentication & Rate Limits**:
  - **No Key**: 10 RPS, shared IP daily budget ($0.10/day).
  - **Free API Key** (`?api_key=YOUR_KEY` or `Authorization: Bearer YOUR_KEY`, provisionable via `POST https://api.openalex.org/api-keys` with `{"email": "you@example.org"}`): **30 RPS**, **$1.00/day free budget**, unlocks deep `cursor=*` pagination.
  - **Per-Endpoint Credit Cost (`meta.cost_usd`)**:
    - **Singleton ID lookups** (`/works/{id}`, `/works/https://doi.org/{doi}`, `/sources/issn:{issn}`): **$0.0000 (100% FREE — never hits 429 budget!)**
    - **Filtered list queries** (`/works?filter=...` without `search=`): **$0.0001**
    - **Full-text search queries** (`/works?search=...`): **$0.001**
    - **Content PDF download** (`content.openalex.org`): **$0.01**

### Key Endpoints & Agent `curl` Patterns
```bash
# 1. Free ($0.00) Singleton Work Lookup by DOI or arXiv DataCite DOI
curl -s "https://api.openalex.org/works/https://doi.org/10.1038/nature14539?mailto=agent@example.org"
curl -s "https://api.openalex.org/works/https://doi.org/10.48550/arXiv.1706.03762?mailto=agent@example.org"

# 2. Free ($0.00) Singleton Journal Lookup by ISSN (returns 2yr_mean_citedness, h_index, i10_index, apc_usd)
curl -s "https://api.openalex.org/sources/issn:2522-5839?mailto=agent@example.org"

# 3. Filtered + Search Work Query (requires API key or available IP budget)
curl -s "https://api.openalex.org/works?search=retrieval+augmented+generation&filter=publication_year:2023-2026,is_oa:true&sort=cited_by_count:desc&per_page=10&api_key=$OPENALEX_API_KEY"

# 4. Citation Graph Traversal (works citing W2626778328)
curl -s "https://api.openalex.org/works?filter=cites:W2626778328&sort=cited_by_count:desc&per_page=10"
```

### Reconstructing `abstract_inverted_index`
OpenAlex stores abstracts as an inverted index (`{"Deep": [0], "learning": [1, 14], ...}`) for copyright compliance. Reconstruct in Python:
```python
def reconstruct_abstract(inv: dict[str, list[int]] | None) -> str | None:
    if not inv:
        return None
    max_idx = max(max(pos) for pos in inv.values() if pos)
    words = [""] * (max_idx + 1)
    for token, positions in inv.items():
        for p in positions:
            words[p] = token
    return " ".join(w for w in words if w)
```

---

## 2. Semantic Scholar (`https://api.semanticscholar.org`)

- **Corpus**: 214M+ papers, 2.49B citations, 79M authors, **SPECTER2** embeddings, AI **TLDRs**, and **500-word full-text body snippets**.
- **Authentication & Rate Limits**:
  - Header: `x-api-key: $S2_API_KEY` (1 RPS dedicated introductory key).
  - Unauthenticated requests share a 1,000 RPS global pool. **Tip**: If `/graph/v1/paper/search` returns `HTTP 429`, fall back immediately to `/graph/v1/paper/search/bulk`, which uses a separate boolean search pool.

### Key Endpoints & Agent `curl` Patterns
```bash
# 1. Relevance Paper Search with BibTeX, TLDR, OpenAccessPdf, and Journal Info
curl -sG "https://api.semanticscholar.org/graph/v1/paper/search" \
  --data-urlencode "query=transformer attention mechanism" \
  --data-urlencode "year=2017-2026" \
  --data-urlencode "fields=paperId,externalIds,title,abstract,year,venue,journal,citationCount,influentialCitationCount,isOpenAccess,openAccessPdf,tldr,citationStyles,authors" \
  --data-urlencode "limit=5"

# 2. Bulk Boolean Search (supports +, |, -, "exact phrase", up to 1,000 results/call)
curl -sG "https://api.semanticscholar.org/graph/v1/paper/search/bulk" \
  --data-urlencode 'query="retrieval augmented generation" + (benchmark | evaluation)' \
  --data-urlencode "sort=citationCount:desc" \
  --data-urlencode "fields=paperId,externalIds,title,abstract,year,citationCount,openAccessPdf,citationStyles"

# 3. Full-Text PDF Snippet Search (~500-word passages extracted from paper body text)
curl -sG "https://api.semanticscholar.org/graph/v1/snippet/search" \
  --data-urlencode "query=scaled dot-product attention complexity" \
  --data-urlencode "limit=5"

# 4. Single Paper Lookup by DOI / ARXIV / PMID / PMCID / CorpusId
curl -s "https://api.semanticscholar.org/graph/v1/paper/ARXIV:1706.03762?fields=title,abstract,tldr,citationStyles,openAccessPdf,citationCount"
```

---

## 3. Crossref (`https://api.crossref.org/v1`)

- **Corpus**: 180M+ official DOI registration records across 100K+ journals and conference serials.
- **Rate Limits (Updated December 1, 2025)**:
  - **Public Pool** (no `mailto`): **5 RPS** single DOI (`concurrency: 1`), **1 RPS** search/list (`concurrency: 1`).
  - **Polite Pool** (append `?mailto=you@example.org`): **10 RPS** single DOI (`concurrency: 3`), **3 RPS** search/list (`concurrency: 3`).
  - **Metadata Plus Pool** (`Crossref-Plus-API-Token: Bearer <key>`): **150 RPS**.

### Key Endpoints & Agent `curl` Patterns
```bash
# 1. Bibliographic Paper Search with Date & ISSN Filters
curl -sG "https://api.crossref.org/v1/works" \
  --data-urlencode "query.bibliographic=deep learning nature" \
  --data-urlencode "filter=from-pub-date:2015,type:journal-article" \
  --data-urlencode "rows=5" \
  --data-urlencode "mailto=agent@example.org"

# 2. Single DOI Metadata Lookup
curl -s "https://api.crossref.org/v1/works/10.1038/nature14539?mailto=agent@example.org"

# 3. Journal Lookup by ISSN or Title Query
curl -s "https://api.crossref.org/v1/journals/1476-4687?mailto=agent@example.org"
curl -s "https://api.crossref.org/v1/journals?query=Nature+Machine+Intelligence&rows=5&mailto=agent@example.org"
```

---

## 4. OpenCitations Index v2 & Meta v1 (`https://api.opencitations.net`)

- **Corpus**: 2B+ open CC0 citation links (`COCI`) and bibliographic metadata (`Meta`).
- **Supported Identifier Prefixes**: `doi:`, `pmid:`, `pmcid:`, `openalex:`, `omid:`, `issn:`.

```bash
# 1. Incoming Citations (who cites this DOI/PMID?)
curl -s "https://api.opencitations.net/index/v2/citations/doi:10.1162/qss_a_00023"

# 2. Outgoing References (what does this DOI cite?)
curl -s "https://api.opencitations.net/index/v2/references/doi:10.1162/qss_a_00023"

# 3. Citation Count Only
curl -s "https://api.opencitations.net/index/v2/citation-count/doi:10.1162/qss_a_00023"

# 4. Bibliographic Metadata Lookup (returns title, author ORCIDs, venue ISSN, volume, issue, page)
curl -s "https://api.opencitations.net/meta/v1/metadata/doi:10.1162/qss_a_00023"
```

---

## 5. DataCite, OpenAIRE Graph & ORCID

```bash
# DataCite REST API (datasets, software, preprints, arXiv DataCite DOIs)
curl -s "https://api.datacite.org/dois?query=climate+model&page\[size\]=5"
curl -sL -H "Accept: application/x-bibtex" "https://data.datacite.org/application/x-bibtex/10.48550/arXiv.1706.03762"

# OpenAIRE Graph API v1 (175M+ research products linked to EU/global grant projects)
curl -sG "https://api.openaire.eu/graph/v1/researchProducts" \
  --data-urlencode "search=quantum error correction" \
  --data-urlencode "type=publication" \
  --data-urlencode "pageSize=5"

# ORCID Public API v3.0 (author disambiguation & publication lists)
curl -s -H "Accept: application/json" "https://pub.orcid.org/v3.0/0000-0002-1825-0097/works"
```
