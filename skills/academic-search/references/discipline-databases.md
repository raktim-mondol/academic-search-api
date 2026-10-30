# Discipline-Specific Literature & Preprint Databases

Covers **arXiv + ar5iv/HTML**, **PubMed (NCBI E-utilities)**, **Europe PMC**, **NCBI PMC BioC Full-Text JSON**, **NCBI PubTator 3.0**, **bioRxiv / medRxiv**, **DBLP**, **INSPIRE-HEP**, **NASA ADS**, and **HuggingFace / ACL Anthology**.

---

## 1. arXiv API + Native BibTeX + arXiv HTML / ar5iv Full Text

- **Search Endpoint**: `GET https://export.arxiv.org/api/query` (returns Atom 1.0 XML).
- **Field Prefixes**: `ti:` (title), `au:` (author), `abs:` (abstract), `cat:` (subject category, e.g., `cs.CL`, `cs.LG`, `stat.ML`, `quant-ph`, `math.PR`), `jr:` (journal ref), `all:`. Combine with `AND`, `OR`, `ANDNOT`.
- **Rate Limit**: Strictly **1 request every 3 seconds (0.33 RPS)**, single concurrent connection.

```bash
# 1. Search arXiv Preprints (Atom 1.0 XML)
curl -sG "https://export.arxiv.org/api/query" \
  --data-urlencode 'search_query=ti:"Attention Is All You Need" OR (all:transformer AND cat:cs.CL)' \
  --data-urlencode "start=0" \
  --data-urlencode "max_results=5" \
  --data-urlencode "sortBy=relevance"

# 2. Fetch Official arXiv BibTeX Directly (no XML parsing needed!)
curl -sL "https://arxiv.org/bibtex/1706.03762"

# 3. Fetch Full-Text LaTeXML HTML (preserves section structure, tables, and LaTeX math!)
curl -sL "https://arxiv.org/html/2402.01680"
# Fallback for older arXiv papers:
curl -sL "https://ar5iv.labs.arxiv.org/html/1706.03762"
```

---

## 2. PubMed (NCBI E-utilities), Europe PMC & PMC BioC Full-Text JSON

### Europe PMC REST JSON API (Fastest single-call JSON for PubMed + PMC)
```bash
# Returns PMID, PMCID, DOI, full abstract, author ORCIDs, MeSH headings, citation counts, and OA PDF URLs
curl -sG "https://www.ebi.ac.uk/europepmc/webservices/rest/search" \
  --data-urlencode "query=(CRISPR base editing) AND (PUB_YEAR:[2023 TO 2026]) AND (OPEN_ACCESS:y)" \
  --data-urlencode "resultType=core" \
  --data-urlencode "format=json" \
  --data-urlencode "pageSize=5"
```

### NCBI PMC BioC Full-Text JSON API (Structured `INTRO`, `METHODS`, `RESULTS`, `DISCUSS`)
```bash
# Retrieve full-text passages in Unicode BioC JSON by PMID or PMCID (for PMC Open Access subset)
curl -s "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/29355051/unicode"
curl -s "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/PMC6142073/unicode"
```

### NCBI PubTator 3.0 AI Entity & Relation API (`https://www.ncbi.nlm.nih.gov/research/pubtator3-api`)
- **Rate Limit**: 3 RPS, no key required.
```bash
# 1. Resolve biomedical mention to normalized entity ID (@CHEMICAL_..., @DISEASE_..., @GENE_...)
curl -s "https://www.ncbi.nlm.nih.gov/research/pubtator3-api/entity/autocomplete/?query=remdesivir&limit=3"

# 2. Search papers by normalized entity or relation
curl -sG "https://www.ncbi.nlm.nih.gov/research/pubtator3-api/search/" \
  --data-urlencode "text=relations:ANY|@CHEMICAL_Doxorubicin|@DISEASE_Neoplasms"

# 3. Export Full-Text BioC JSON with Entity Annotations
curl -s "https://www.ncbi.nlm.nih.gov/research/pubtator3-api/publications/export/biocjson?pmids=29355051&full=true"
```

### NCBI Entrez E-utilities (`https://eutils.ncbi.nlm.nih.gov/entrez/eutils`)
- **Rate Limit**: 3 RPS without key; 10 RPS with `&api_key=$NCBI_API_KEY`.
```bash
# Step 1: esearch (get PMIDs) -> Step 2: esummary / efetch
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=mRNA+vaccine+safety&retmode=json&retmax=5"
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=38572754,29355051&retmode=json"
```

---

## 3. bioRxiv & medRxiv CSHL API (`https://api.biorxiv.org`)

```bash
# 1. Fetch preprints in date interval (server = biorxiv or medrxiv, cursor = 0, 100, ...)
curl -s "https://api.biorxiv.org/details/biorxiv/2026-10-01/2026-10-28/0/json"

# 2. Lookup preprint by DOI and find its published journal DOI (pubs endpoint)
curl -s "https://api.biorxiv.org/details/biorxiv/10.1101/2023.11.15.567231/na/json"
curl -s "https://api.biorxiv.org/pubs/biorxiv/10.1101/2023.11.15.567231/na/json"
```

---

## 4. DBLP Computer Science Bibliography (`https://dblp.org`)

- **Endpoints**:
  - Publications: `https://dblp.org/search/publ/api?q={query}&format=json&h={limit}&f={offset}`
  - Venues (Journals/Conferences): `https://dblp.org/search/venue/api?q={query}&format=json&h={limit}`
  - Authors: `https://dblp.org/search/author/api?q={query}&format=json&h={limit}`
  - Direct BibTeX (`param=0` standard, `param=1` condensed, `param=2` with crossref): `https://dblp.org/rec/{key}.bib?param=0`
- **2026 Anubis v1.27.0 Note**: `dblp.org` uses an Anubis `metarefresh` challenge (`HTTP 202`) on cloud IPs. `acadsearch` automatically solves `/.within.website/x/cmd/anubis/api/pass-challenge` after 1.08s and reuses the `dblp_org-auth` session cookie.

---

## 5. INSPIRE-HEP & NASA ADS (Physics, High-Energy Physics & Astrophysics)

```bash
# INSPIRE-HEP Literature Search (supports SPIRES syntax like 'a E.Witten.1 and topcite 500+')
curl -s "https://inspirehep.net/api/literature?q=ads/cft+maldacena&sort=mostcited&size=5"

# INSPIRE-HEP Direct BibTeX or LaTeX (format=bibtex | latex-eu | latex-us)
curl -s "https://inspirehep.net/api/literature/451647?format=bibtex"
curl -s "https://inspirehep.net/api/doi/10.1103/PhysRevLett.19.1264?format=bibtex"

# NASA ADS Search & BibTeX Export (requires Authorization: Bearer $ADS_API_KEY)
curl -sG "https://api.adsabs.harvard.edu/v1/search/query" \
  -H "Authorization: Bearer $ADS_API_KEY" \
  --data-urlencode 'q=author:"Rubin, V" year:1970-1985 property:refereed' \
  --data-urlencode "fl=bibcode,title,author,year,pub,doi,abstract,citation_count"

curl -sX POST "https://api.adsabs.harvard.edu/v1/export/bibtex" \
  -H "Authorization: Bearer $ADS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"bibcode": ["1980ApJ...238..471R"]}'
```
