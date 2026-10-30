# Commercial Bibliometric, Publisher TDM & AI-Native Academic APIs

Covers **Clarivate Web of Science (Starter v1, Expanded, and JCR Journals v1)**, **Elsevier (Scopus Search, Abstract Retrieval, ScienceDirect Full-Text, Serial Title CiteScore/SJR/SNIP)**, **Wiley Online Library TDM API v1**, **Springer Nature (Meta v2, Open Access JATS, Full-Text TDM)**, **IEEE Xplore v1**, **12+ Society & University Press Publishers (Taylor & Francis, SAGE, OUP, CUP, ACM, ACS, APS, IOP, RSC, MDPI, Frontiers, PLOS)**, **Dimensions & The Lens**, **Google Scholar (SerpApi/Serper)**, **Consensus MCP**, **scite MCP**, **Elicit v2**, and **FutureHouse PaperQA2**.

---

## 1. Clarivate Web of Science (WoS) & Journal Citation Reports (JCR) APIs

Clarivate exposes three distinct REST APIs authenticated via the `X-ApiKey: $WOS_API_KEY` HTTP header ([Clarivate Developer Portal](https://developer.clarivate.com/apis)):

### A. Web of Science Starter API v1 (`https://api.clarivate.com/apis/wos-starter/v1`)
- **Purpose**: Real-time document & journal search with Web of Science Core Collection **Times Cited** counts and article links ([Clarivate WoS Starter](https://developer.clarivate.com/apis/wos-starter)).
- **Rate Limits**: 1–5 RPS, up to 5,000 requests/day on institutional starter plans.
- **Supported Field Tags in `q`**:
  - `TS=(...)` Topic (Title + Abstract + Author Keywords + Keywords Plus)
  - `TI=(...)` Title | `AU=(...)` Author | `AI=(...)` ResearcherID / ORCID
  - `SO=(...)` Source/Journal Title | `IS=(...)` ISSN (`XXXX-XXXX`)
  - `DO=(...)` DOI | `PMID=(...)` PubMed ID | `UT=(WOS:...)` Web of Science Accession UID
  - `PY=(2022-2026)` Publication Year | `DT=(Article OR Review)` Document Type | `OG=(...)` Organization
- **Supported `db` Values**: `WOS` (Web of Science Core Collection), `WOK` (All Databases), `BIOABS`, `BCI`, `MEDLINE`, `PPRN` (Preprint Citation Index), `DIIDW` (Derwent Innovations Index), `DRCI` (Data Citation Index).

```bash
# 1. Search WoS Core Collection Documents (via acadsearch or curl)
acadsearch papers "solid state battery" --providers wos --year-min 2023 --limit 5

curl -sG "https://api.clarivate.com/apis/wos-starter/v1/documents" \
  -H "X-ApiKey: $WOS_API_KEY" \
  -H "Accept: application/json" \
  --data-urlencode "db=WOS" \
  --data-urlencode "q=TS=(graph neural network) AND PY=(2023-2026) AND DT=(Article)" \
  --data-urlencode "limit=10" \
  --data-urlencode "page=1" \
  --data-urlencode "sortField=TC+D"

# 2. Query WoS Starter Journals by ISSN
curl -sG "https://api.clarivate.com/apis/wos-starter/v1/journals" \
  -H "X-ApiKey: $WOS_API_KEY" \
  --data-urlencode "issn=1476-4687"
```

### B. Web of Science Journals API / Journal Citation Reports (JCR v1) (`https://api.clarivate.com/apis/wos-journals/v1`)
- **Purpose**: Official **Journal Impact Factor (JIF)**, **5-Year JIF**, **Journal Citation Indicator (JCI)**, **JIF Quartile (`Q1`–`Q4`)**, **JIF Percentile (`0`–`100`)**, **Immediacy Index**, and **Eigenfactor** ([Clarivate WoS Journals Client](https://github.com/clarivate/wosjournals-python-client/blob/main/docs/JournalsApi.md)).
- **Endpoints**:
  - `GET /journals` — filter by `q` (ISSN or title), `edition` (`SCIE`, `SSCI`, `AHCI`, `ESCI`), `categoryCode`, `jcrYear`, `jif`, `jifQuartile` (`Q1`, `Q2`, `Q3`, `Q4`), `jifPercentile`, `jci`.
  - `GET /journals/{id}` — journal profile by JCR ID.
  - `GET /journals/{id}/reports/year/{year}` — complete JCR metric report for a given year.
  - `GET /journals/{id}/citing/year/{year}` & `GET /journals/{id}/cited/year/{year}` — journal-to-journal citation matrix.

```bash
# Search JCR Q1 Journals and fetch 2025 JIF & Quartile Report
curl -sG "https://api.clarivate.com/apis/wos-journals/v1/journals" \
  -H "X-ApiKey: $WOS_API_KEY" \
  --data-urlencode "q=2522-5839" \
  --data-urlencode "jcrYear=2025" \
  --data-urlencode "jifQuartile=Q1"
```

### C. Web of Science Expanded API (`https://wos-api.clarivate.com/api/wos`)
- **Purpose**: Full item-level record export (`optionView=FR` Full Record vs. `SR` Short Record), complete author affiliation hierarchies, grant funding (`FUND_ACK`), cited references (`/api/wos/references`), citing articles (`/api/wos/citing`), and related records (`/api/wos/related`) ([Clarivate WoS Expanded](https://developer.clarivate.com/apis/wos)).
- **Rate Limits**: 2–5 RPS; plans range from 50,000 to 3,000,000 Full Records/year ([Clarivate WoS Expanded](https://developer.clarivate.com/apis/wos)).

```bash
# Retrieve Full Record (FR) from WoS Expanded API
curl -sG "https://wos-api.clarivate.com/api/wos" \
  -H "X-ApiKey: $WOS_API_KEY" \
  --data-urlencode "databaseId=WOS" \
  --data-urlencode "usrQuery=DO=(10.1038/nature14539)" \
  --data-urlencode "count=1" \
  --data-urlencode "firstRecord=1" \
  --data-urlencode "optionView=FR"
```

---

## 2. Elsevier Scopus, ScienceDirect & Serial Title APIs (`https://api.elsevier.com`)

- **Authentication**: Pass `X-ELS-APIKey: $ELSEVIER_API_KEY` (and `X-ELS-Insttoken: $ELSEVIER_INSTTOKEN` for institutional subscriber views such as `COMPLETE`, `REF`, and `FULL`) ([Elsevier Dev Portal](https://dev.elsevier.com/api_docs.html)).
- **Zero-Key Fallback in `acadsearch`**: When `ELSEVIER_API_KEY` is not set, `acadsearch papers "<query>" --providers scopus` (or `elsevier` / `sciencedirect`) automatically queries Elsevier's official Crossref Member `78` catalog (**25,529,399+ ScienceDirect/Elsevier DOIs**) and enriches top results via OpenAlex's free (`$0.00`) singleton lookup.

### A. Scopus Search API (`GET /content/search/scopus`)
- **Boolean Field Operators**: `TITLE-ABS-KEY(...)`, `TITLE(...)`, `ABS(...)`, `KEY(...)`, `AUTH(...)`, `AFFIL(...)`, `SRCTITLE(...)`, `ISSN(...)`, `DOI(...)`, `PUBYEAR > 2022`, `SUBJAREA(COMP OR ENGI)`, `FUND-SPONSOR(...)`, `OPENACCESS(1)`.
- **Quota**: 20,000 requests/week (2–9 RPS depending on view `STANDARD` vs. `COMPLETE`).

```bash
curl -sG "https://api.elsevier.com/content/search/scopus" \
  -H "X-ELS-APIKey: $ELSEVIER_API_KEY" \
  -H "Accept: application/json" \
  --data-urlencode "query=TITLE-ABS-KEY(solid state battery) AND PUBYEAR > 2023" \
  --data-urlencode "view=STANDARD" \
  --data-urlencode "count=10"
```

### B. Scopus Abstract Retrieval API (`GET /content/abstract/...`)
- **Identifier Routes**: `/content/abstract/doi/{doi}`, `/content/abstract/scopus_id/{scopus_id}`, `/content/abstract/eid/{eid}`, `/content/abstract/pubmed_id/{pmid}` ([Elsevier Abstract Retrieval](https://dev.elsevier.com/documentation/AbstractRetrievalAPI.wadl)).
- **Views**: `META`, `META_ABS` (includes full abstract), `REF` (includes complete bibliography references), `FULL` (complete Scopus record) ([Scopus Views](https://dev.elsevier.com/sc_abstract_retrieval_views.html)).
- **Direct BibTeX / RIS Export**: Set `Accept: application/x-bibtex` or `Accept: application/x-research-info-systems`.

```bash
curl -s "https://api.elsevier.com/content/abstract/doi/10.1016/j.cell.2023.01.001?view=FULL" \
  -H "X-ELS-APIKey: $ELSEVIER_API_KEY" \
  -H "Accept: application/json"
```

### C. ScienceDirect Full-Text Article Retrieval API (`GET /content/article/...`)
- **Routes**: `GET https://api.elsevier.com/content/article/doi/{doi}?view=FULL` or `/content/article/pii/{pii}?view=FULL` ([Elsevier TDM Guide](https://dev.elsevier.com/tecdoc_text_mining.html)).
- **Formats**: `Accept: application/json` or `Accept: text/xml` (returns full Elsevier XML DTD with structured `<ce:sections>`, tables, and equations). Automatically invoked by `acadsearch context "<doi>"` when `ELSEVIER_API_KEY` is set.

### D. Elsevier Serial Title API — Journal CiteScore, SJR & SNIP (`GET /content/serial/title/issn/{issn}`)
```bash
# Returns CiteScoreCurrentMetric, CiteScoreTracker, SJR, SNIP, and subject percentiles
curl -s "https://api.elsevier.com/content/serial/title/issn/1476-4687?view=ENHANCED" \
  -H "X-ELS-APIKey: $ELSEVIER_API_KEY" \
  -H "Accept: application/json"
```

---

## 3. Wiley Online Library TDM API v1 & Crossref Member 311 (`wiley`)

Wiley separates **metadata discovery** from **full-text PDF Text and Data Mining (TDM) retrieval** ([Wiley TDM Guide](https://ua-libraries-research-data-services.github.io/UALIB_ScholarlyAPI_Cookbook/python/wiley-tdm.html), [Wiley TDM Client](https://github.com/WileyLabs/tdm-client)):

### A. Full-Text PDF Download via Wiley TDM API v1
- **Endpoint**: `GET https://api.wiley.com/onlinelibrary/tdm/v1/articles/{url_encoded_doi}`
- **Authentication**: Header `Wiley-TDM-Client-Token: $WILEY_TDM_TOKEN` (UUID token obtained from the Wiley Online Library TDM dashboard; also requires institutional IP entitlement for paywalled articles, while Open Access Wiley articles resolve via both TDM and `/doi/pdfdirect/{doi}`) ([Wiley TDM Client](https://github.com/WileyLabs/tdm-client)).
- **Rate Limit**: Up to **3 requests/second**; official Python client is `pip install wiley-tdm` (`TDM_API_TOKEN`).

```bash
# 1. Download full-text PDF directly from Wiley TDM API (note %2F for /)
curl -sL "https://api.wiley.com/onlinelibrary/tdm/v1/articles/10.1002%2Fnet.22207" \
  -H "Wiley-TDM-Client-Token: $WILEY_TDM_TOKEN" \
  -o paper.pdf

# 2. Extract full-text sections into agent prompt via acadsearch (uses WILEY_TDM_TOKEN or OA PDF automatically)
acadsearch context "10.1002/bte2.20230041" --query "solid electrolyte interphase" --format markdown
```

### B. Searching Wiley Journals & Articles (12.23M+ DOIs, Zero Keys Required)
- Wiley's official Crossref Member ID is **`311`** (**12,237,680+ registered DOIs** across *Advanced Materials*, *Angewandte Chemie*, *Adv. Energy Mater.*, *WIREs*, *Cochrane*, etc.).
- Running `acadsearch papers "<query>" --providers wiley` queries `https://api.crossref.org/v1/members/311/works` and automatically enriches every Wiley paper via OpenAlex's free (`$0.00`) singleton lookup (`GET https://api.openalex.org/works/https://doi.org/{doi}`) to attach reconstructed abstracts, citation counts, Open Access PDF links (`https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}`), and BibTeX!

```bash
# Search Wiley papers with full abstract, OA PDF, citation count & BibTeX (no API key needed)
acadsearch papers "all-solid-state lithium battery" --providers wiley --limit 5 --format markdown
```

---

## 4. Springer Nature API Suite (`https://api.springernature.com`)

- **2026 Endpoint Migration Alert**: Springer Nature retired `spdi.public.springernature.app` on **August 7, 2026**. All Full-Text TDM requests must now target `https://api.springernature.com/xmldata/jats` ([Springer Full Text API](https://dev.springernature.com/docs/api-endpoints/fulltext-api/)).
- **Zero-Key Fallback**: When `SPRINGER_API_KEY` is not set, `acadsearch papers "<query>" --providers springer_nature` searches Crossref Member **`297`** (**19,060,623+ Springer, Nature, BMC, and Palgrave DOIs**) + OpenAlex `$0.00` singleton enrichment.

```bash
# 1. Meta v2 API (16M+ Nature/Springer/BMC documents)
curl -sG "https://api.springernature.com/meta/v2/json" \
  --data-urlencode 'q=title:"protein folding" AND year:2025' \
  --data-urlencode "p=10" \
  --data-urlencode "api_key=$SPRINGER_API_KEY"

# 2. Open Access Full-Text JATS XML API (1.5M+ OA articles with complete <sec> body XML)
curl -sG "https://api.springernature.com/openaccess/jats" \
  --data-urlencode "q=doi:10.1038/s41467-024-00001-x" \
  --data-urlencode "api_key=$SPRINGER_API_KEY"

# 3. Subscriber Full-Text TDM JATS XML API (post-Aug 2026 endpoint)
curl -sG "https://api.springernature.com/xmldata/jats" \
  --data-urlencode "q=doi:10.1007/978-3-662-54664-2" \
  --data-urlencode "api_key=$SPRINGER_API_KEY"
```

---

## 5. IEEE Xplore API v1 (`https://ieeexploreapi.ieee.org`)

- **Authentication**: `?apikey=$IEEE_API_KEY` (10 RPS, 200 calls/day default developer tier) ([IEEE Xplore API](https://developer.ieee.org/docs/read/Searching_the_IEEE_Xplore_Metadata_API)).
- **Zero-Key Fallback**: When `IEEE_API_KEY` is not set, `acadsearch papers "<query>" --providers ieee` searches Crossref Member **`263`** (**6,248,530+ IEEE transactions, journals, conferences, and standards**) + OpenAlex `$0.00` singleton enrichment.

```bash
curl -sG "https://ieeexploreapi.ieee.org/api/v1/search/articles" \
  --data-urlencode "querytext=(6G AND \"reconfigurable intelligent surface\")" \
  --data-urlencode "start_year=2023" \
  --data-urlencode "content_type=Journals" \
  --data-urlencode "max_records=10" \
  --data-urlencode "apikey=$IEEE_API_KEY"
```

---

## 6. Major Academic Publishers & Societies Reference Table ("etc.")

All 16 publisher keys below can be passed directly to `acadsearch papers "<query>" --providers <publisher_key>` (or queried via `GET https://api.crossref.org/v1/members/{member_id}/works?query.bibliographic={q}&mailto=agent@example.org`):

| `acadsearch` Provider Key | Publisher / Society Name | Verified Crossref Member ID | Registered DOIs | Dedicated / Native Full-Text & TDM API |
| :--- | :--- | :---: | :---: | :--- |
| `elsevier` / `scopus` / `sciencedirect` | **Elsevier BV (ScienceDirect / Cell Press / Lancet)** | `78` | 25,529,399 | `https://api.elsevier.com/content/article/doi/{doi}?view=FULL` (`X-ELS-APIKey`) |
| `springer_nature` / `springer` / `nature` | **Springer Nature (Nature, Springer, BMC, Palgrave)** | `297` | 19,060,623 | `https://api.springernature.com/openaccess/jats` & `/xmldata/jats` (`api_key`) |
| `wiley` | **John Wiley & Sons (Wiley Online Library)** | `311` | 12,237,680 | `https://api.wiley.com/onlinelibrary/tdm/v1/articles/{doi}` (`Wiley-TDM-Client-Token`) |
| `taylor_francis` | **Taylor & Francis / Informa UK (Routledge, CRC)** | `301` | 8,352,307 | Crossref Member `301` + Unpaywall OA PDF |
| `oup` / `oxford` | **Oxford University Press (OUP Academic)** | `286` | 7,604,556 | Crossref Member `286` + OUP Academic TDM + Europe PMC |
| `ieee` / `ieee_xplore` | **IEEE (Institute of Electrical and Electronics Engineers)** | `263` | 6,248,530 | `https://ieeexploreapi.ieee.org/api/v1/search/articles` (`apikey`) |
| `sage` | **SAGE Publications** | `179` | 3,774,476 | Crossref Member `179` + Unpaywall OA PDF |
| `cup` / `cambridge` | **Cambridge University Press (Cambridge Core)** | `56` | 2,570,664 | Crossref Member `56` + Unpaywall OA PDF |
| `mdpi` | **MDPI AG (100% Gold Open Access)** | `1968` | 2,246,637 | Direct Gold OA PDF via OpenAlex / Unpaywall |
| `acs` | **American Chemical Society (ACS Publications)** | `316` | 2,240,477 | Crossref Member `316` + CAS Common Chemistry API (`https://commonchemistry.cas.org/api`) |
| `iop` | **IOP Publishing (Institute of Physics)** | `266` | 1,301,427 | Crossref Member `266` + arXiv / INSPIRE-HEP |
| `rsc` | **Royal Society of Chemistry (RSC)** | `292` | 1,144,191 | Crossref Member `292` + Unpaywall OA PDF |
| `frontiers` | **Frontiers Media SA (100% Gold Open Access)** | `1965` | 849,113 | Direct Gold OA PDF & JATS XML via OpenAlex / Europe PMC |
| `aps` | **American Physical Society (Physical Review)** | `16` | 819,198 | `http://harvest.aps.org/v2/journals/articles` + arXiv / INSPIRE-HEP |
| `acm` | **Association for Computing Machinery (ACM DL)** | `320` | 779,656 | Crossref Member `320` + DBLP + OpenAlex (ACM Open) |
| `plos` | **Public Library of Science (PLOS ONE / Biology)** | `340` | 418,626 | `https://api.plos.org/search?q=...&wt=json` + NCBI PMC BioC JSON |

---

## 7. AI-Native Academic Search & Citation Verification (MCP & REST)

| Provider | Hosted MCP / REST Endpoint | Key Agent Tools & Parameters |
|---|---|---|
| **Consensus** | MCP: `https://mcp.consensus.app/mcp`<br>REST: `https://api.consensus.app/v1/quick_search` | `search`: `query`, `year_min`, `year_max`, `study_types` (`rct`, `meta-analysis`, `systematic review`), `sjr_max` (`1`=Q1..`4`=Q4), `sample_size_min`, `human`, `medical_mode` |
| **scite** | MCP: `https://api.scite.ai/mcp` (`POST` JSON-RPC 2.0, `Bearer scite_...`) | `search_literature` (Smart Citations: supporting vs. contrasting counts & full-text snippets) + 17 FDA/MHRA/clinical-trial tools |
| **Elicit** | MCP: `https://elicit.com/api/mcp`<br>REST: `https://elicit.com/api/v2` | `POST /api/v2/search/papers` (`query`, `maxResults`, excludes retractions by default), `POST /api/v2/sessions/systematic-reviews`, `POST /api/v2/sessions/reports` (100 RPM IP limit) |
| **FutureHouse** | PyPI: `paper-qa>=5` & `uvx futurehouse-mcp@latest stdio` | `Crow` (fast cited search), `Falcon` (deep literature review), `Owl` ("Has anyone done X before?"), `Phoenix` (chemistry synthesis) |
| **Google Scholar** | SerpApi: `https://serpapi.com/search?engine=google_scholar`<br>Serper: `POST https://google.serper.dev/scholar` | `engine=google_scholar` (`q`, `as_ylo`, `as_yhi`, `cites`) + `engine=google_scholar_cite` (`q={result_id}` -> returns official BibTeX link & APA/MLA/Chicago citations) |
