# Journal Directories, Open-Access Resolvers & Universal BibTeX

Covers **DOAJ v4**, **Unpaywall v2**, **Universal DOI Content Negotiation (`doi.org`)**, **CORE v3**, **HAL Open Archive**, and **Zenodo**.

---

## 1. Universal DOI Content Negotiation (`https://doi.org/{doi}`)

Any registered DOI (300M+ across Crossref, DataCite, mEDRA, ISTIC, JaLC) returns official citation formats directly via the HTTP `Accept` header (`-L` required to follow redirects to `citation.doi.org` / `data.datacite.org`):

```bash
# 1. Official BibTeX Entry
curl -sLH "Accept: application/x-bibtex; charset=utf-8" "https://doi.org/10.1038/nature14539"

# 2. CSL-JSON (Citeproc JSON — structured authors, title, container-title, issued, volume, page, ISSN)
curl -sLH "Accept: application/vnd.citationstyles.csl+json" "https://doi.org/10.1038/nature14539"

# 3. RIS Format (EndNote / Zotero / Mendeley)
curl -sLH "Accept: application/x-research-info-systems" "https://doi.org/10.1038/nature14539"

# 4. Pre-Formatted Bibliography String (9,000+ CSL styles: apa, ieee, nature, harvard1, vancouver)
curl -sLH "Accept: text/x-bibliography; style=ieee; locale=en-US" "https://doi.org/10.1038/nature14539"
```

---

## 2. DOAJ API v4 (`https://doaj.org/api/v4`)

- **Corpus**: 21,000+ peer-reviewed Gold/Diamond Open Access journals and 10.5M+ articles.
- **Important Escaping Rule**: Forward slashes `/` inside the path query (such as in DOIs) must be escaped as `\/` (`%5C/` in URL encoding). Append `.exact` to any string field for exact matching.

```bash
# 1. Search Open Access Journals by Title or Subject (returns APCs in USD, CC license, publisher, ISSNs)
curl -s "https://doaj.org/api/v4/search/journals/bibjson.title:%22PLOS%20ONE%22?pageSize=5"

# 2. Lookup Journal by Exact ISSN
curl -s "https://doaj.org/api/v4/search/journals/issn:1932-6203?pageSize=1"

# 3. Search Open Access Articles (with full-text PDF links and abstracts)
curl -s "https://doaj.org/api/v4/search/articles/crispr%20gene%20editing?pageSize=5"

# 4. Lookup DOAJ Article by DOI (note %5C/ escaping for /)
curl -s "https://doaj.org/api/v4/search/articles/doi:10.3389%5C/fpsyg.2013.00479"
```

---

## 3. Unpaywall API v2 (`https://api.unpaywall.org/v2`)

- **Purpose**: Resolves any DOI to legal Open Access full-text PDF URLs across 50,000+ publisher and institutional repositories.
- **Rate Limit**: 100,000 calls/day free (`?email=YOUR_EMAIL` required).
- **2026 Deprecation Notice**: `GET /v2/search` was permanently retired on **September 18, 2026** (`HTTP 410 Gone`). Use OpenAlex `/works?search=...&filter=is_oa:true` for text search, and Unpaywall `/v2/{doi}` for DOI-to-PDF resolution.

```bash
# Resolve DOI to best Open Access PDF URL, license, and version (publishedVersion vs submittedVersion)
curl -s "https://api.unpaywall.org/v2/10.1038/nature14539?email=agent@example.org"
```

---

## 4. CORE API v3 (`https://api.core.ac.uk/v3`)

- **Corpus**: 452M+ metadata records and **57M+ pre-extracted full-text strings** (`fullText` field directly inside JSON response).
- **Auth & Limits**: `Authorization: Bearer $CORE_API_KEY`; 0.5 RPS guest, 10 RPM registered academic.

```bash
# Search works and receive inline fullText string + downloadUrl
curl -sG "https://api.core.ac.uk/v3/search/works" \
  -H "Authorization: Bearer $CORE_API_KEY" \
  --data-urlencode "q=federated learning privacy" \
  --data-urlencode "limit=5"
```

---

## 5. HAL Open Archive & Zenodo REST API

```bash
# HAL Open Archive (Solr query syntax; wt=json, wt=bibtex, or wt=xml-tei for full-text TEI)
curl -s "https://api.hal.science/search/?q=title_t:(transformer)&wt=json&rows=5&fl=halId_s,title_s,authFullName_s,doiId_s,abstract_s,fileMain_s,label_bibtex"

# Zenodo REST API (search records; supports Accept: application/x-bibtex on individual records)
curl -s "https://zenodo.org/api/records?q=large+language+model+benchmark&size=5"
curl -s -H "Accept: application/x-bibtex" "https://zenodo.org/api/records/5788550"
```
