# Academic Search Database API, MCP, SDK, CLI & Agent Skill Reference Manual

## Executive Summary

Autonomous research agents, scientific Retrieval-Augmented Generation (RAG) pipelines, and automated manuscript/LaTeX authoring workflows require far more structured retrieval than general web search engines provide. Academic search databases index persistent scholarly identifiers (**DOI**, **arXiv ID**, **PMID**, **PMCID**, **ISSN-L**, **ORCID**, **ROR**, **OpenAlex ID**, **OCI**), journal scientometrics (**2-Year Mean Citedness**, **Journal Impact Factor (JIF)**, **CiteScore**, **SJR**, **SNIP**, **h-index**, **i10-index**, **DOAJ/APC status**), deterministic bibliography formats (**BibTeX**, **CSL-JSON**, **RIS**, **LaTeX `\bibitem`**), and structured full-text representations (**arXiv LaTeXML HTML / ar5iv**, **NCBI PMC BioC JSON**, **JATS XML**, and **500-word body-text snippets**).

This manual provides:
1. **Exhaustive Technical API & MCP Documentation for 30+ Academic Databases** across five architectural tiers, including exact base URLs, endpoints, query syntax, authentication headers, rate limits, 2026 deprecations/anti-bot changes, and pros/cons.
2. **Complete Documentation for the `acadsearch` Unified Implementation** packaged in `/home/user/workspace/academic-search-api`, which delivers a working **Python SDK**, **Command-Line Interface (`acadsearch`)**, **FastAPI OpenAPI 3.1 REST Server**, **Model Context Protocol (MCP) Server (`stdio` and Streamable HTTP `/mcp`)**, and a modular **Agent Skill (`skills/academic-search/SKILL.md`)**.

---

## Master Comparison Matrix of Academic Databases

| # | Provider / Database | Category & Discipline Focus | Corpus Size | Primary Base URL / MCP Endpoint | Auth Mode | Rate Limits & Pricing | Paper Search | Journal Metrics | Native BibTeX | Abstract | Full-Text / PDF Context |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **1** | **OpenAlex** | Global Open Scholarly Graph (All Disciplines) | 300M+ core works, 250K+ journals ([OpenAlex API](https://help.openalex.org/api/)) | `https://api.openalex.org` | Optional `?api_key=` or `?mailto=` ([OpenAlex Auth](https://help.openalex.org/api/authentication.md)) | **10 RPS** (no key, $0.10/d); **30 RPS** (free key, $1/d); **Singleton ID lookups = $0.00 FREE** ([OpenAlex Auth](https://help.openalex.org/api/authentication.md)) | Yes | Yes (`2yr_mean_citedness`, `h_index`, `i10_index`, `apc_usd`) | Via DOI / Synth | Yes (`abstract_inverted_index`) | OA `pdf_url` + `content.openalex.org` |
| **2** | **Semantic Scholar** | Global AI Scholarly Graph (CS, Biomed, All) | 214M+ papers, 2.49B citations ([Semantic Scholar API](https://www.semanticscholar.org/product/api)) | `https://api.semanticscholar.org/graph/v1` | Optional `x-api-key` header ([Semantic Scholar Usage](https://semanticscholar.readthedocs.io/en/latest/usage.html)) | Free; **1 RPS** dedicated key; shared 1,000 RPS pool ([Semantic Scholar API](https://www.semanticscholar.org/product/api)) | Yes (`/paper/search` & `/search/bulk`) | Venue ISSN & type | Yes (`citationStyles.bibtex`) | Yes + AI `tldr` | **500-word body snippets** (`/snippet/search`) + `openAccessPdf` |
| **3** | **Crossref** | Official DOI Registration Agency | 180M+ DOIs, 100K+ journals ([Crossref Docs](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/)) | `https://api.crossref.org/v1` | Polite Pool `?mailto=`; Plus `Bearer` ([Crossref Rate Limits](https://www.crossref.org/blog/announcing-changes-to-rest-api-rate-limits/)) | Polite: **10 RPS** single DOI / **3 RPS** search; Public: **5 RPS** / **1 RPS** ([Crossref Rate Limits](https://www.crossref.org/blog/announcing-changes-to-rest-api-rate-limits/)) | Yes (`/v1/works`) | Yes (`/v1/journals/{issn}`) | Yes (`doi.org` content negotiation) | Yes (JATS XML/text) | Publisher license & PDF links |
| **4** | **DOI Content Negotiation** | Universal Citation Resolver (Crossref/DataCite/mEDRA) | 300M+ registered DOIs ([DOI Content Negotiation](https://github.com/wentorai/research-plugins/blob/main/skills/literature/metadata/doi-content-negotiation/SKILL.md)) | `https://doi.org/{doi}` | None required ([DataCite Resolver](https://support.datacite.org/docs/datacite-content-resolver)) | Free public resolution | By DOI | Container ISSN | **Official `application/x-bibtex`** | In `csl+json` | Landing URL redirect |
| **5** | **OpenCitations** | Open Citation Graph (`COCI` & `Meta`) | 2B+ citation links ([OpenCitations Quickstart](https://github.com/opencitations/oc_docs/blob/main/docs/api/quickstart.md)) | `https://api.opencitations.net/index/v2` & `/meta/v1` | Optional `Authorization` token ([OpenCitations Quickstart](https://github.com/opencitations/oc_docs/blob/main/docs/api/quickstart.md)) | 100% Free, high throughput | By DOI, PMID, PMCID, OMID | Venue ISSN in Meta v1 | Synth from Meta v1 | No | Citation timespan & self-citation flags |
| **6** | **DataCite** | Research Datasets, Software, Preprints | 60M+ DataCite DOIs ([DataCite REST API](https://support.datacite.org/docs/rest-api)) | `https://api.datacite.org/dois` | None for read ([DataCite REST API](https://support.datacite.org/docs/rest-api)) | Free public JSON:API | Yes (`?query=`) | Repository / Publisher | Yes (`Accept: application/x-bibtex`) | Yes (`descriptions`) | Direct dataset/preprint content URLs |
| **7** | **OpenAIRE Graph** | Global & European Open Science Graph | 175M+ research products, 3M+ grants ([OpenAIRE Graph Docs](https://graph.openaire.eu/docs/next/apis/graph-api/making-requests/)) | `https://api.openaire.eu/graph/v1` | None (optional Bearer token) ([OpenAIRE Graph Docs](https://graph.openaire.eu/docs/next/apis/graph-api/making-requests/)) | Free public tier | Yes (`/researchProducts`) | `/dataSources` | Synth | Yes | OA links & EU/global project funding |
| **8** | **ORCID Public API** | Researcher Identity & Bibliography | 20M+ researcher profiles ([ORCID Search Docs](https://info.orcid.org/ufaqs/how-do-i-use-the-orcid-search-api/)) | `https://pub.orcid.org/v3.0` | Public or `/read-public` token ([ORCID Model](https://github.com/ORCID/orcid-model/blob/master/src/main/resources/record_3.0/README.md)) | Free public tier (up to 10,000 results) | Author works (`/{orcid}/works`) | Journal title/ISSN per work | Embedded `citation-value` BibTeX | Work summaries | External DOIs/URLs |
| **9** | **DOAJ API v4** | Gold & Diamond Open Access Journals | 21,000+ OA journals, 10.5M+ articles ([DOAJ API v4 Docs](https://doaj.org/api/v4/docs)) | `https://doaj.org/api/v4` | None required ([DOAJ API v4 Docs](https://doaj.org/api/v4/docs)) | 100% Free public REST API | Yes (`/search/articles/{q}`) | **Yes (`/search/journals/{q}`, APCs, licenses)** | Synth | Yes (`bibjson.abstract`) | Direct Gold OA full-text links |
| **10** | **Unpaywall v2** | Legal Open-Access PDF Resolver | 50M+ OA articles across 50K+ repos ([Unpaywall API](https://unpaywall.org/products/api)) | `https://api.unpaywall.org/v2/{doi}` | `?email=YOUR_EMAIL` ([Unpaywall API](https://unpaywall.org/products/api)) | Free up to **100,000 calls/day** (`/v2/search` retired Sept 18, 2026) ([Unpaywall API](https://unpaywall.org/products/api)) | By DOI only | `journal_is_oa`, `journal_is_in_doaj` | No | No | **`best_oa_location.url_for_pdf`** |
| **11** | **CORE API v3** | Open Repository Full-Text Aggregator | 452M+ records, **57M+ hosted full texts** ([CORE API Services](https://core.ac.uk/services/api)) | `https://api.core.ac.uk/v3` | `Bearer $CORE_API_KEY` ([CORE API Guide](https://github.com/wentorai/research-plugins/blob/main/skills/literature/fulltext/core-api-guide/SKILL.md)) | 0.5 RPS guest; 10 RPM free academic key ([CORE API Services](https://core.ac.uk/services/api)) | Yes (`/v3/search/works`) | `/v3/data-providers` | Synth | Yes | **Inline `fullText` string in JSON** + `downloadUrl` |
| **12** | **HAL & Zenodo** | Multidisciplinary Open Archives | 4M+ HAL records, 4M+ Zenodo records ([HAL API](https://api.hal.science/docs/search), [Zenodo Dev](https://developers.zenodo.org/)) | `https://api.hal.science/search/` & `https://zenodo.org/api/records` | None for search (optional Zenodo Bearer) | Free (Zenodo: 60 RPM guest / 100 RPM token) | Yes (Solr / Elasticsearch) | HAL `revue` domain | **Yes (`wt=bibtex` / `Accept: application/x-bibtex`)** | Yes | **HAL `wt=xml-tei` full text** & Zenodo files |
| **13** | **arXiv + ar5iv/HTML** | STEM Preprints (CS, Math, Physics, Q-Bio, Stat) | 2.6M+ preprints ([arXiv API Manual](https://info.arxiv.org/help/api/user-manual.html)) | `https://export.arxiv.org/api/query` & `https://arxiv.org/html/{id}` | None required ([arXiv API Terms](https://info.arxiv.org/help/api/tou.html)) | **1 req / 3s (0.33 RPS)**, single connection ([arXiv API Terms](https://info.arxiv.org/help/api/tou.html)) | Yes (Atom 1.0 XML) | `arxiv:journal_ref` | **Yes (`https://arxiv.org/bibtex/{id}`)** | Yes (`<summary>`) | **Native LaTeXML HTML (`arxiv.org/html`, `ar5iv`) & PDF** |
| **14** | **PubMed (NCBI E-utilities)** | Biomedical & Life Sciences Literature | 36M+ citations & abstracts ([NCBI E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25497/)) | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/` | Optional `&api_key=` ([NCBI E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25497/)) | **3 RPS** (no key); **10 RPS** (free NCBI key) ([NCBI E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25497/)) | Yes (`esearch` -> `esummary`/`efetch`) | Medline TA & ISSN | Via PMID/DOI | Yes (`efetch` XML/text) | Links to PMC (`elink`) |
| **15** | **Europe PMC** | Biomedical Full-Text & Text-Mined Graph | 33M+ publications, 10.2M+ full texts ([Europe PMC REST](https://europepmc.org/RestfulWebService)) | `https://www.ebi.ac.uk/europepmc/webservices/rest` | None required ([Europe PMC REST](https://europepmc.org/RestfulWebService)) | Free high-throughput REST JSON/XML | Yes (`/search?resultType=core&format=json`) | Journal ISSN & OA flag | Synth / RIS | Yes (`abstractText`) | **`/{pmcid}/fullTextXML`** + OA PDF render |
| **16** | **NCBI PMC BioC JSON** | Structured Biomedical Full-Text Sections | 6.5M+ PMC Open Access full texts ([NCBI BioC-PMC](https://www.ncbi.nlm.nih.gov/research/bionlp/APIs/BioC-PMC/)) | `https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi` | None required ([NCBI BioC-PMC](https://www.ncbi.nlm.nih.gov/research/bionlp/APIs/BioC-PMC/)) | Free public REST (`BioC_json/{id}/unicode`) | By PMID or PMCID | In passage infons | No | Section `ABSTRACT` | **Segmented `INTRO`, `METHODS`, `RESULTS`, `DISCUSS`, `TABLE`, `FIG`** |
| **17** | **NCBI PubTator 3.0** | Biomedical AI Entity & Relation Search | 1B+ annotations on 36M abstracts & 6M full texts ([PubTator 3.0 Docs](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/paper-lookup/references/pubtator.md)) | `https://www.ncbi.nlm.nih.gov/research/pubtator3-api` | None required ([PubTator 3.0 Docs](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/paper-lookup/references/pubtator.md)) | **3 RPS** free ([PubTator 3.0 Docs](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/paper-lookup/references/pubtator.md)) | Entity & relation search (`/search/`) | Journal name | No | Annotated abstract | **`/publications/export/biocjson?pmids=...&full=true`** |
| **18** | **bioRxiv & medRxiv** | Biology & Clinical Medicine Preprints | 300K+ preprints ([bioRxiv API](https://api.biorxiv.org/)) | `https://api.biorxiv.org` | None required ([bioRxiv API](https://api.biorxiv.org/)) | Free cursor pagination (100/page) | By date interval or DOI (`/details/...`) | Published journal DOI link (`/pubs/...`) | Via DOI | Yes (`abstract`) | JATS XML link (`jatsxml`) & PDF |
| **19** | **DBLP** | Computer Science Bibliography | 7.5M+ CS papers, 6,000+ venues ([DBLP API FAQ](https://dblp.org/faq/13501473)) | `https://dblp.org/search/publ/api` & `/venue/api` | None (Anubis v1.27.0 `metarefresh` cookie on cloud IPs) | Free polite sequential access (~1–2 RPS) | Yes (`/search/publ/api?format=json`) | **Yes (`/search/venue/api`)** | **Official `/rec/{key}.bib?param=0`** | No (metadata + `ee` link) | Electronic edition (`ee`) OA links |
| **20** | **INSPIRE-HEP** | High-Energy Physics, Cosmology & Math | 1.7M+ HEP records ([INSPIRE REST API](https://github.com/inspirehep/rest-api-doc/blob/master/README.md)) | `https://inspirehep.net/api/literature` & `/journals` | None required ([INSPIRE REST API](https://github.com/inspirehep/rest-api-doc/blob/master/README.md)) | **15 requests per 5s window (3 RPS)** per IP ([INSPIRE REST API](https://github.com/inspirehep/rest-api-doc/blob/master/README.md)) | Yes (SPIRES & ES syntax) | Yes (`/api/journals`) | **Yes (`?format=bibtex`, `latex-eu`, `latex-us`)** | Yes (`abstracts[0].value`) | Direct arXiv & publisher OA links |
| **21** | **NASA ADS** | Astrophysics, Astronomy & Physics | 16M+ physics & space science records ([NASA ADS MCP](https://github.com/pipeworx-io/mcp-nasa-ads)) | `https://api.adsabs.harvard.edu/v1` | `Bearer $ADS_API_KEY` ([NASA ADS MCP](https://github.com/pipeworx-io/mcp-nasa-ads)) | Free key: **5,000 requests/day** | Yes (`/v1/search/query`) | `bibstem` & refereed status | **Yes (`POST /v1/export/bibtex`)** | Yes | ADS scans, arXiv PDFs, `/v1/metrics` |
| **22** | **Elsevier (Scopus / ScienceDirect / Serial Title)** | Commercial Bibliometrics & Full Text | 95M+ Scopus records, 25.5M+ Elsevier DOIs, 29K+ serials ([Elsevier Dev Portal](https://dev.elsevier.com/api_docs.html)) | `https://api.elsevier.com/content` | `X-ELS-APIKey` (+ `X-ELS-Insttoken`); zero-key via Member `78` | 2–10 RPS (20,000/wk Scopus Search) | Yes (`/search/scopus`, `/search/sciencedirect`, Member `78`) | **Yes (`/serial/title/issn/{issn}` -> CiteScore, SJR, SNIP)** | Yes (`Accept: application/x-bibtex`) | Yes (`/abstract/doi/{doi}`) | **ScienceDirect `/article/doi/{doi}?view=FULL`** |
| **22b** | **Wiley Online Library (TDM API v1 & Member 311)** | Major Academic Publisher (Journals, Books & TDM PDF) | 12.23M+ Wiley DOIs across 1,600+ journals ([Wiley TDM Guide](https://ua-libraries-research-data-services.github.io/UALIB_ScholarlyAPI_Cookbook/python/wiley-tdm.html)) | `https://api.wiley.com/onlinelibrary/tdm/v1/articles/{doi}` & `/v1/members/311/works` | `Wiley-TDM-Client-Token: $WILEY_TDM_TOKEN`; zero-key search via Member `311` ([Wiley TDM Client](https://github.com/WileyLabs/tdm-client)) | TDM: up to **3 RPS** PDF download; Search: **3 RPS** Polite Pool | Yes (`--providers wiley`) | Via ISSN & OpenAlex | Yes (`doi.org` content negotiation) | Yes (via OpenAlex singleton enrichment) | **Full-Text PDF via Wiley TDM API (`/tdm/v1/articles/{doi}`) & `/doi/pdfdirect`** |
| **23** | **Springer Nature** | Publisher Metadata, Open Access JATS & TDM | 19.06M+ DOIs, 16M+ Meta v2 docs, 1.5M+ OA JATS articles ([Springer Meta API](https://dev.springernature.com/docs/api-endpoints/meta-api/)) | `https://api.springernature.com` | `?api_key=$SPRINGER_API_KEY`; zero-key via Member `297` ([Springer OA API](https://dev.springernature.com/docs/api-endpoints/open-access/)) | Free dev key (500–5,000 calls/day) | Yes (`/meta/v2/json`, `/openaccess/json`, Member `297`) | Journal title & ISSN | Yes (via DOI) | Yes | **Full-text JATS XML (`/openaccess/jats` & `/xmldata/jats`)** |
| **24** | **IEEE Xplore** | Electrical Engineering, CS & Standards | 6.25M+ IEEE articles & standards ([IEEE Xplore API](https://developer.ieee.org/docs/read/Searching_the_IEEE_Xplore_Metadata_API)) | `https://ieeexploreapi.ieee.org/api/v1/search/articles` | `?apikey=$IEEE_API_KEY`; zero-key via Member `263` ([IEEE Xplore API](https://developer.ieee.org/docs/read/Searching_the_IEEE_Xplore_Metadata_API)) | 10 RPS, 200 calls/day free dev tier | Yes (Boolean, fielded & Member `263`) | IEEE Publication Title & ISSN | Yes (via DOI) | Yes (`abstract`) | Open Access full-text article retrieval |
| **25** | **Clarivate Web of Science (Starter, Expanded & JCR)** | Commercial Citation Index & Impact Factor (JIF) | 90M+ WoS Core records, 21K+ JCR journals ([Clarivate WoS Starter](https://developer.clarivate.com/apis/wos-starter), [WoS Expanded](https://developer.clarivate.com/apis/wos)) | `https://api.clarivate.com/apis/wos-starter/v1`, `/wos-journals/v1` & `https://wos-api.clarivate.com/api/wos` | `X-ApiKey: $WOS_API_KEY` ([Clarivate WoS Client](https://github.com/clarivate/wosstarter_python_client)) | Starter: 1–5 RPS (5K/d); Expanded: 2–5 RPS (50K–3M FR/yr) | Yes (`/documents` & `/api/wos`) | **Yes (`/wos-journals/v1/journals` -> JIF, JCI, Quartile Q1–Q4)** | Via DOI | Yes (Expanded `optionView=FR`) | Full Record metadata, funding, & cited references |
| **25b** | **Major Society & University Press Publishers** | Taylor & Francis (`301`), OUP (`286`), SAGE (`179`), CUP (`56`), MDPI (`1968`), ACS (`316`), IOP (`266`), RSC (`292`), Frontiers (`1965`), APS (`16`), ACM (`320`), PLOS (`340`) | 35M+ publisher DOIs ([Crossref Members](https://www.crossref.org/members-area/)) | `https://api.crossref.org/v1/members/{id}/works` + `harvest.aps.org` + `api.plos.org` | Zero-key Polite Pool (`?mailto=`) | 3 RPS search / 10 RPS singleton DOI | Yes (`--providers taylor_francis,oup,sage,cup,acm,acs,aps,plos`) | ISSN + OpenAlex metrics | Yes (`doi.org` content negotiation) | Yes (OpenAlex singleton enrichment) | Unpaywall & Publisher Gold/Green OA PDFs |
| **26** | **Dimensions & The Lens** | Linked Grants, Patents, Trials & Papers | 140M+ papers linked to patents & grants ([Dimensions DSL](https://docs.dimensions.ai/dsl/api.html), [Lens API](https://about.lens.org/lens-apis/)) | `https://app.dimensions.ai/api/dsl/v2` & `https://api.lens.org/scholarly/search` | Dimensions JWT (`POST /api/auth`); Lens `Bearer` | Dimensions: **30 RPM**; Lens: 14-day trial / Member ([Dimensions DSL](https://docs.dimensions.ai/dsl/api.html), [Lens API](https://about.lens.org/lens-apis/)) | Yes (DSL v2 & JSON POST) | Field Citation Ratio (FCR), RCR | Synth | Yes | Cross-domain patent & clinical trial citations |
| **27** | **Google Scholar (SerpApi / Serper)** | Broadest Web Academic & Legal Case Crawl | ~300M–400M academic web docs & case law ([SerpApi MCP](https://serpapi.com/integrations/mcp)) | `https://serpapi.com/search?engine=google_scholar` & `https://google.serper.dev/scholar` | API Key (`api_key` / `X-API-KEY`) | Serper: $0.30–$1/1K, 50–300 RPS; SerpApi: $0.015/search | Yes (`google_scholar`) | `google_scholar_profiles` | **Yes (`google_scholar_cite` -> BibTeX link)** | Snippet only | Direct `[PDF]` links from SERP |
| **28** | **Consensus MCP** | AI Evidence & Study-Design Search | 200M–220M+ papers ([Consensus MCP Docs](https://docs.consensus.app/docs/mcp)) | `https://mcp.consensus.app/mcp` & `/v1/quick_search` | OAuth or `Bearer $CONSENSUS_API_KEY` ([Consensus MCP Docs](https://docs.consensus.app/docs/mcp)) | **1 RPS**; Free (30/mo), Pro (250/mo), Deep (1,000/mo), Enterprise ([Consensus MCP Docs](https://docs.consensus.app/docs/mcp)) | Yes (`search` MCP tool) | **`sjr_max` (`1`=Q1..`4`=Q4) quartile filter** | Via Enterprise DOI | Yes + Pro `takeaway` | Study-type (`rct`, `meta-analysis`) & `sample_size_min` |
| **29** | **scite MCP** | Smart Citations (Supporting vs. Contrasting) | 1.6B+ citation statements across 44+ publishers ([scite MCP Overview](https://docs.scite.ai/mcp/overview)) | `https://api.scite.ai/mcp` (`POST` JSON-RPC 2.0) | OAuth 2.1 or `Bearer scite_...` ([scite MCP Overview](https://docs.scite.ai/mcp/overview)) | Premium / Pro monthly plan quota ([scite MCP Overview](https://docs.scite.ai/mcp/overview)) | Yes (`search_literature` + 17 FDA/trial tools) | Journal editorial tallies | Via DOI | Yes | **Full-text supporting/contrasting citation snippets** |
| **30** | **Elicit v2 & FutureHouse PaperQA2** | Systematic Reviews & Deep Literature RAG | Elicit: 138M papers + 545K trials ([Elicit API Ref](https://docs.elicit.com/llms.txt)); PaperQA2: Open-source + hosted ([PaperQA2 Repo](https://github.com/Future-House/paper-qa?tab=readme-ov-file)) | `https://elicit.com/api/v2` (`https://elicit.com/api/mcp`) & `futurehouse-mcp` | Bearer `$ELICIT_API_KEY` / `$FUTUREHOUSE_API_KEY` | Elicit: **100 RPM per IP** (5-min IP ban if exceeded) ([Elicit API Ref](https://docs.elicit.com/llms.txt)) | Yes (`POST /v2/search/papers` & `Crow`/`Falcon`) | Journal quartile filter & quality score | Via DOI | Yes | **Auditable full-text data extraction tables (`CSV`/`XLSX`)** |

---

## Tier 1: Open Global Scholarly Graphs & Identifier Registries

### OpenAlex (`https://api.openalex.org`)

- **Architecture, Licensing, and 2026 Budget Model**:
  - Maintained by OurResearch, OpenAlex indexes **300M+ curated core scholarly works** (plus ~60% additional non-core records accessible via `corpus=all`), **250,000+ journals/sources**, **100M+ authors**, and **110,000+ institutions** under a **CC0 public-domain license** ([OpenAlex API](https://help.openalex.org/api/)).
  - **Authentication**: Supply a free verified API key via `?api_key=YOUR_KEY` or `Authorization: Bearer YOUR_KEY`, or provision one programmatically via `POST https://api.openalex.org/api-keys` with `{"email": "you@example.org"}` ([OpenAlex Auth](https://help.openalex.org/api/authentication.md)).
  - **Rate Limits and Per-Endpoint Credit Accounting (`meta.cost_usd`)**:
    - Throughput ceiling: **10 RPS** without a key, **30 RPS** with a free or prepaid API key, and **50 RPS** on an annual plan ([OpenAlex Auth](https://help.openalex.org/api/authentication.md)).
    - Daily budget: **$0.10/day** shared per IP without a key; **$1.00/day** dedicated free budget with a free API key ([OpenAlex Auth](https://help.openalex.org/api/authentication.md)).
    - **Crucial Agent Optimization — Zero-Cost Singleton Lookups**:
      - **Singleton ID lookups** (`GET /works/{id}`, `GET /works/https://doi.org/{doi}`, `GET /works/pmid:{pmid}`, `GET /works/pmcid:{pmcid}`, `GET /sources/issn:{issn}`) cost **`$0.0000` (100% free)** and **still return `200 OK` even when the keyless IP daily search budget is exhausted** ([OpenAlex API](https://help.openalex.org/api/)).
      - Furthermore, because DataCite mints `10.48550/arXiv.{arxiv_id}` for every arXiv preprint, calling `GET https://api.openalex.org/works/https://doi.org/10.48550/arXiv.{arxiv_id}` resolves any arXiv paper's OpenAlex work record, citation count, and reference graph at **$0.00 cost**.
      - Filtered list queries (`/works?filter=...`) cost `$0.0001`, full-text search queries (`/works?search=...`) cost `$0.001`, and PDF downloads from `content.openalex.org` cost `$0.01` ([OpenAlex API](https://help.openalex.org/api/)).
- **Journal & Venue Metrics (`/sources`)**:
  - Querying `GET https://api.openalex.org/sources?search={journal_name}` or `GET https://api.openalex.org/sources/issn:{issn}` returns:
    - `issn_l` (linking ISSN) and `issn` array (print and electronic ISSNs).
    - `summary_stats.2yr_mean_citedness`: OpenAlex's open-access equivalent of the **2-Year Journal Impact Factor (JIF)** (e.g., `24.99` for Nature Machine Intelligence, `ISSN 2522-5839`).
    - `summary_stats.h_index` and `summary_stats.i10_index`.
    - `is_oa`, `is_in_doaj`, `apc_usd` (Article Processing Charge in USD), `host_organization_name` (publisher), `works_count`, `cited_by_count`, and `counts_by_year` ([OpenAlex API](https://help.openalex.org/api/)).
- **Abstract Reconstruction (`abstract_inverted_index`)**:
  - OpenAlex stores work abstracts as a token-to-position map (`{"The": [0], "dominant": [1], "sequence": [2], ...}`). Agents must reconstruct the plaintext string by allocating an array up to the maximum index and joining tokens by space (implemented in `acadsearch.utils.reconstruct_abstract`).
- **MCP Server**: `DeyangLiu123/openalex-mcp` (`uvx --from git+https://github.com/DeyangLiu123/openalex-mcp.git openalex-mcp`) or the unified `acadsearch-mcp` server ([DeyangLiu123 openalex-mcp](https://github.com/DeyangLiu123/openalex-mcp)).

---

### Semantic Scholar (`https://api.semanticscholar.org`)

- **Architecture and Authentication**:
  - Operated by the Allen Institute for AI (Ai2), indexing **214M+ papers**, **2.49B citations**, and **79M authors** across `/graph/v1`, `/recommendations/v1`, and `/datasets/v1` ([Semantic Scholar API](https://www.semanticscholar.org/product/api)).
  - Authenticate via header `x-api-key: $S2_API_KEY` (1 RPS introductory rate limit; unauthenticated callers share a global 1,000 RPS pool) ([Semantic Scholar Usage](https://semanticscholar.readthedocs.io/en/latest/usage.html)).
- **Core Endpoints & Parameters**:
  - **Relevance Search**: `GET /graph/v1/paper/search?query={q}&year={YYYY-YYYY}&openAccessPdf=&venue={venue}&minCitationCount={n}&fields={fields}&limit={1..100}` ([Semantic Scholar Usage](https://semanticscholar.readthedocs.io/en/latest/usage.html)).
  - **Bulk Boolean Search (High-Reliability Fallback)**: `GET /graph/v1/paper/search/bulk?query={boolean_query}&sort=citationCount:desc&fields={fields}`. Supports `+` (AND), `|` (OR), `-` (NOT), and `"exact phrase"`, returning up to 1,000 papers per request ([Semantic Scholar Usage](https://semanticscholar.readthedocs.io/en/latest/usage.html)).
  - **Full-Text PDF Snippet Search (`/graph/v1/snippet/search`)**:
    - `GET https://api.semanticscholar.org/graph/v1/snippet/search?query={focus_query}&paperIds={comma_separated_ids}&limit={1..50}`
    - Returns **~500-word passages extracted directly from the full text** of open-access and partner PDFs, complete with `snippet.section` (`Introduction`, `Methods`, `Results`, `Discussion`), `snippet.snippetKind`, character offsets, and relevance `score` ([Semantic Scholar Usage](https://semanticscholar.readthedocs.io/en/latest/usage.html)).
  - **Single & Batch Lookups**: `GET /graph/v1/paper/{id}` and `POST /graph/v1/paper/batch` (up to 500–1,000 IDs per POST) accepting `DOI:...`, `ARXIV:...`, `PMID:...`, `PMCID:...`, `ACL:...`, `MAG:...`, or `CorpusId:...` ([Semantic Scholar Usage](https://semanticscholar.readthedocs.io/en/latest/usage.html)).
  - **Essential `fields` Projection**: Always request `paperId,externalIds,url,title,abstract,venue,publicationVenue,year,referenceCount,citationCount,influentialCitationCount,isOpenAccess,openAccessPdf,fieldsOfStudy,publicationTypes,publicationDate,journal,citationStyles,authors,tldr` (plus `embedding.specter_v2` when dense 768-dim vectors are needed) ([Semantic Scholar Usage](https://semanticscholar.readthedocs.io/en/latest/usage.html)).

---

### Crossref (`https://api.crossref.org/v1`) & Universal DOI Content Negotiation (`https://doi.org`)

- **Crossref REST API**:
  - Official DOI registration metadata catalog covering **180M+ scholarly works** and **100,000+ journal serials** ([Crossref Docs](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/)).
  - **Endpoints**:
    - `GET /v1/works?query.bibliographic={q}&filter=from-pub-date:{YYYY},until-pub-date:{YYYY},issn:{ISSN},type:journal-article&rows={n}&mailto={email}`
    - `GET /v1/works/{doi}?mailto={email}`
    - `GET /v1/journals/{issn}?mailto={email}` and `GET /v1/journals?query={title}&rows={n}&mailto={email}` ([Crossref Docs](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/)).
  - **Rate Limits (Effective December 1, 2025)**:
    - **Public Pool** (no `mailto`): **5 RPS** on single-DOI lookups (`concurrency: 1`) and **1 RPS** on list/search queries (`concurrency: 1`) ([Crossref Rate Limits](https://www.crossref.org/blog/announcing-changes-to-rest-api-rate-limits/)).
    - **Polite Pool** (free; append `?mailto=you@example.com` or `User-Agent: App/1.0 (mailto:you@example.com)`): **10 RPS** on single-DOI lookups (`concurrency: 3`) and **3 RPS** on list/search queries (`concurrency: 3`) ([Crossref Rate Limits](https://www.crossref.org/blog/announcing-changes-to-rest-api-rate-limits/)).
    - **Metadata Plus Pool** (`Crossref-Plus-API-Token: Bearer <key>`): **150 RPS** with no concurrency limit ([Crossref Rate Limits](https://www.crossref.org/blog/announcing-changes-to-rest-api-rate-limits/)).
- **Universal DOI Content Negotiation (`https://doi.org/{doi}`)**:
  - Works across **all 300M+ registered DOIs** (Crossref, DataCite, mEDRA) without an API key by setting the HTTP `Accept` header and following redirects (`curl -LH` / `follow_redirects=True`) ([DOI Content Negotiation](https://github.com/wentorai/research-plugins/blob/main/skills/literature/metadata/doi-content-negotiation/SKILL.md), [DataCite Resolver](https://support.datacite.org/docs/datacite-content-resolver)):
    - `Accept: application/x-bibtex; charset=utf-8` -> Official BibTeX entry.
    - `Accept: application/vnd.citationstyles.csl+json` -> Structured Citeproc CSL-JSON.
    - `Accept: application/x-research-info-systems` -> RIS reference manager format.
    - `Accept: text/x-bibliography; style=apa` (or `ieee`, `nature`, `chicago-author-date`, `vancouver`) -> Pre-rendered citation string.

---

### OpenCitations (`https://api.opencitations.net`), DataCite (`https://api.datacite.org`), OpenAIRE (`https://api.openaire.eu`), and ORCID (`https://pub.orcid.org`)

- **OpenCitations Index API v2 & Meta API v1**:
  - Queries 2B+ open CC0 citation links using persistent identifier prefixes (`doi:`, `pmid:`, `pmcid:`, `openalex:`, `omid:`, `issn:`) ([OpenCitations Quickstart](https://github.com/opencitations/oc_docs/blob/main/docs/api/quickstart.md)):
    - `GET https://api.opencitations.net/index/v2/citations/doi:{doi}` (incoming citing works, with `oci`, `citing`, `cited`, `creation` date, `timespan` in ISO 8601 duration, `journal_sc`, and `author_sc` self-citation flags).
    - `GET https://api.opencitations.net/index/v2/references/doi:{doi}` (outgoing referenced works).
    - `GET https://api.opencitations.net/index/v2/citation-count/doi:{doi}` (total incoming citation count).
    - `GET https://api.opencitations.net/meta/v1/metadata/doi:{doi}` (title, authors with ORCIDs, venue with ISSN and OpenAlex source ID, volume, issue, page, publisher) ([OpenCitations Quickstart](https://github.com/opencitations/oc_docs/blob/main/docs/api/quickstart.md)).
- **DataCite REST (`https://api.datacite.org/dois`) & GraphQL (`https://api.datacite.org/graphql`)**:
  - Primary registry for **60M+ research datasets, scientific software packages, preprints (including arXiv DataCite DOIs), and grey literature** ([DataCite REST API](https://support.datacite.org/docs/rest-api)).
  - Supports `GET /dois?query={q}&resource-type-id=dataset|software|preprint&page[size]=25` and direct BibTeX export via `https://data.datacite.org/application/x-bibtex/{doi}` ([DataCite Resolver](https://support.datacite.org/docs/datacite-content-resolver)).
- **OpenAIRE Graph API (`https://api.openaire.eu/graph`)**:
  - Indexes **175M+ research products** (`publications`, `datasets`, `software`, `other`) linked to **3M+ European and global research grant projects** ([OpenAIRE Graph Docs](https://graph.openaire.eu/docs/next/apis/graph-api/making-requests/)).
  - Endpoint: `GET https://api.openaire.eu/graph/v1/researchProducts?search={q}&type=publication&page=1&pageSize=10&sortBy=relevance%20DESC` ([OpenAIRE Graph Docs](https://graph.openaire.eu/docs/next/apis/graph-api/making-requests/)).
- **ORCID Public API v3.0 (`https://pub.orcid.org/v3.0`)**:
  - Disambiguates authors and retrieves verified bibliography lists via `GET https://pub.orcid.org/v3.0/{orcid}/works` (with `Accept: application/json`) and Solr search `GET https://pub.orcid.org/v3.0/search/?q=family-name:LeCun+AND+given-names:Yann` ([ORCID Search Docs](https://info.orcid.org/ufaqs/how-do-i-use-the-orcid-search-api/), [ORCID Model](https://github.com/ORCID/orcid-model/blob/master/src/main/resources/record_3.0/README.md)).

---

## Tier 2: Journal Directories, Open-Access Resolvers & Repositories

### DOAJ (Directory of Open Access Journals) API v4 (`https://doaj.org/api/v4`)

- **Architecture and Query Rules**:
  - Indexes **21,000+ peer-reviewed Open Access journals** and **10.5M+ open-access articles** ([DOAJ API v4 Docs](https://doaj.org/api/v4/docs)).
  - **Endpoints**:
    - Journal search: `GET https://doaj.org/api/v4/search/journals/{search_query}?page={p}&pageSize={n}&sort={field}`
    - Article search: `GET https://doaj.org/api/v4/search/articles/{search_query}?page={p}&pageSize={n}` ([DOAJ API v4 Docs](https://doaj.org/api/v4/docs)).
  - **Elasticsearch Dot-Notation & Slash Escaping**:
    - Query nested fields with dot notation: `bibjson.title:"PLOS ONE"`, `bibjson.journal.title.exact:"Nature Communications"`, `issn:1932-6203`, `doi:10.3389%5C/fpsyg.2013.00479` ([DOAJ API v4 Docs](https://doaj.org/api/v4/docs)).
    - **Critical Rule**: Forward slashes `/` in the path query parameter must be escaped as `\/` (`%5C/` in URLs) ([DOAJ API v4 Docs](https://doaj.org/api/v4/docs)).
  - **Journal Metadata Returned**: Print and electronic ISSNs (`pissn`, `eissn`), publisher name and country, APC policy (`bibjson.apc.has_apc` and `bibjson.apc.max` in USD/EUR/GBP), Creative Commons license type (`bibjson.license[0].type`), review process (`Peer review`, `Double blind peer review`), and `oa_start` year ([DOAJ API v4 Docs](https://doaj.org/api/v4/docs)).

---

### Unpaywall API v2 (`https://api.unpaywall.org/v2`)

- **DOI-to-PDF Resolution**:
  - `GET https://api.unpaywall.org/v2/{doi}?email=YOUR_EMAIL` resolves any DOI across 50,000+ publisher and institutional repositories, returning `is_oa` (boolean), `oa_status` (`gold`, `hybrid`, `bronze`, `green`, `closed`), `journal_is_oa`, `journal_is_in_doaj`, and `best_oa_location` (`url_for_pdf`, `url_for_landing_page`, `version`, `license`, `host_type`) ([Unpaywall API](https://unpaywall.org/products/api)).
  - **Rate Limit**: Free for up to **100,000 requests per day** ([Unpaywall API](https://unpaywall.org/products/api)).
  - **2026 Breaking Change**: Unpaywall permanently retired `GET /v2/search` on **September 18, 2026** (now returning `HTTP 410 Gone`). All full-text search queries must be routed to `https://api.openalex.org/works?search=...&filter=is_oa:true` ([Unpaywall API](https://unpaywall.org/products/api)).

---

### CORE API v3 (`https://api.core.ac.uk/v3`), HAL (`https://api.hal.science`), and Zenodo (`https://zenodo.org/api`)

- **CORE API v3**:
  - Aggregates **452M+ metadata records** and **57M+ hosted full-text papers** from 15,000+ repositories ([CORE API Services](https://core.ac.uk/services/api)).
  - `GET https://api.core.ac.uk/v3/search/works?q={query}&limit={n}` (with `Authorization: Bearer $CORE_API_KEY`) returns work metadata **plus the complete pre-extracted `fullText` string** directly inside the JSON object when hosted by CORE ([CORE API Guide](https://github.com/wentorai/research-plugins/blob/main/skills/literature/fulltext/core-api-guide/SKILL.md)).
- **HAL Open Archive API (`https://api.hal.science/search/`)**:
  - Uses Apache Solr query syntax (`q=title_t:(transformer)&wt=json|bibtex|xml-tei&fl=halId_s,title_s,authFullName_s,doiId_s,abstract_s,fileMain_s,label_bibtex`), returning direct PDF links (`fileMain_s`), BibTeX (`label_bibtex` or `wt=bibtex`), and GROBID-extracted TEI XML (`wt=xml-tei`) ([HAL API](https://api.hal.science/docs/search)).
- **Zenodo REST API (`https://zenodo.org/api/records`)**:
  - Searches 4M+ open-access publications, datasets, and software releases via `GET https://zenodo.org/api/records?q={query}&size={n}` and exports BibTeX via `Accept: application/x-bibtex` ([Zenodo Dev](https://developers.zenodo.org/)).

---

## Tier 3: Discipline-Specific Preprint & Literature Databases

### arXiv API (`https://export.arxiv.org`), Native BibTeX & arXiv HTML / ar5iv

- **Atom 1.0 Search API**:
  - Endpoint: `GET https://export.arxiv.org/api/query?search_query={query}&id_list={ids}&start={0}&max_results={n}&sortBy=relevance|lastUpdatedDate|submittedDate&sortOrder=descending` ([arXiv API Manual](https://info.arxiv.org/help/api/user-manual.html)).
  - Field prefixes: `ti:` (title), `au:` (author), `abs:` (abstract), `cat:` (category, e.g., `cs.CL`, `cs.AI`, `math.OC`, `quant-ph`), `jr:` (journal reference), `rn:` (report number), `all:` (all fields), combined with uppercase `AND`, `OR`, `ANDNOT` ([arXiv API Manual](https://info.arxiv.org/help/api/user-manual.html)).
  - **Best Practice Query Construction**: Unquoted multi-word `all:word1 word2` queries on arXiv split tokens loosely. Always construct `ti:"{exact_phrase}" OR abs:"{exact_phrase}" OR (all:word1 AND all:word2)` for high-precision title and topic matching (implemented automatically in `acadsearch.providers.arxiv.search_arxiv`).
  - **Rate Limit**: Strictly **1 request every 3 seconds (0.33 RPS)** and **1 concurrent connection** ([arXiv API Terms](https://info.arxiv.org/help/api/tou.html)).
- **Native BibTeX Endpoint**:
  - `GET https://arxiv.org/bibtex/{arxiv_id}` returns the official `@misc` / `@article` BibTeX record in plain text without requiring XML parsing.
- **Full-Text LaTeXML HTML (`arxiv.org/html` & `ar5iv`)**:
  - `GET https://arxiv.org/html/{arxiv_id}` (and fallback `https://ar5iv.labs.arxiv.org/html/{arxiv_id}`) serves clean HTML5 compiled directly from the author's LaTeX source (`<section class="ltx_section">`), preserving section headings, tables, and inline LaTeX math far more accurately than PDF text extraction ([arXiv MCP Server](https://github.com/cyanheads/arxiv-mcp-server/blob/main/README.md)).

---

### PubMed (NCBI E-utilities), Europe PMC, NCBI PMC BioC JSON & PubTator 3.0

1. **Europe PMC RESTful Web Service (`https://www.ebi.ac.uk/europepmc/webservices/rest`)**:
   - Fastest single-call JSON interface for **33M+ PubMed and PMC records**:
     - `GET /search?query=(...) AND (PUB_YEAR:[2022 TO 2026]) AND (OPEN_ACCESS:y)&resultType=core&format=json&pageSize=25`
     - Returns `pmid`, `pmcid`, `doi`, `title`, `authorList` (with ORCIDs and affiliations), `journalInfo` (title, ISSN, volume, issue), `abstractText`, `citedByCount`, `meshHeadingList`, and `fullTextUrlList` (direct OA PDF URLs) in a single HTTP request ([Europe PMC REST](https://europepmc.org/RestfulWebService)).
     - Additional endpoints: `/{source}/{id}/citations`, `/{source}/{id}/references`, `/{pmcid}/fullTextXML`, and `/annotations_api/annotationsByArticleIds` ([Europe PMC REST](https://europepmc.org/RestfulWebService)).
2. **NCBI PMC Open Access BioC JSON API (`https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi`)**:
   - `GET https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/{pmid_or_pmcid}/unicode`
   - Returns the full text of PMC Open Access articles segmented into JSON `passages`, each annotated with `infons.section_type` (`TITLE`, `ABSTRACT`, `INTRO`, `METHODS`, `RESULTS`, `FIG`, `TABLE`, `DISCUSS`, `CONCL`, `REF`) ([NCBI BioC-PMC](https://www.ncbi.nlm.nih.gov/research/bionlp/APIs/BioC-PMC/)).
3. **NCBI PubTator 3.0 AI Entity & Relation API (`https://www.ncbi.nlm.nih.gov/research/pubtator3-api`)**:
   - Normalizes biomedical concepts (`chemical`, `disease`, `gene`, `species`, `variant`, `cellline`) across 36M PubMed abstracts and 6M PMC full texts ([PubTator 3.0 Docs](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/paper-lookup/references/pubtator.md)):
     - Entity resolution: `GET /entity/autocomplete/?query=remdesivir&concept=chemical&limit=3` -> `{"_id": "@CHEMICAL_remdesivir", "db_id": "C000606551"}`
     - Entity/Relation literature search: `GET /search/?text=relations:ANY|@CHEMICAL_Doxorubicin|@DISEASE_Neoplasms&page=1`
     - Full-text BioC JSON export: `GET /publications/export/biocjson?pmids=29355051&full=true` (rate limit: **3 RPS**) ([PubTator 3.0 Docs](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/paper-lookup/references/pubtator.md)).
4. **NCBI Entrez E-utilities (`https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`)**:
   - 9 CGI endpoints (`einfo.fcgi`, `esearch.fcgi`, `epost.fcgi`, `esummary.fcgi`, `efetch.fcgi`, `elink.fcgi`, `egquery.fcgi`, `espell.fcgi`, `ecitmatch.cgi`) across 38 NCBI databases ([NCBI E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25497/)).
   - Rate limit: **3 RPS** without an API key; **10 RPS** with a free `api_key` parameter ([NCBI E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25497/)).

---

### bioRxiv & medRxiv CSHL API (`https://api.biorxiv.org`)

- **Endpoints**:
  - Content Details by Interval or DOI: `GET https://api.biorxiv.org/details/{biorxiv|medrxiv}/{YYYY-MM-DD/YYYY-MM-DD_or_DOI}/{cursor_or_na}/json` ([bioRxiv API](https://api.biorxiv.org/)).
  - Preprint-to-Published-Journal Linking: `GET https://api.biorxiv.org/pubs/{biorxiv|medrxiv}/{preprint_doi}/na/json` returns `published_doi`, `published_journal`, and `preprint_title`, enabling agents to upgrade a preprint citation to its peer-reviewed journal version automatically ([bioRxiv API](https://api.biorxiv.org/pubs/help)).

---

### DBLP Computer Science Bibliography (`https://dblp.org`)

- **Core Endpoints**:
  - Publication Search: `GET https://dblp.org/search/publ/api?q={query}&format=json&h={1..1000}&f={offset}&c={completions}` ([DBLP API FAQ](https://dblp.org/faq/13501473)).
  - Venue (Journal & Conference) Search: `GET https://dblp.org/search/venue/api?q={query}&format=json&h={limit}` ([DBLP API FAQ](https://dblp.org/faq/13501473)).
  - Author Search: `GET https://dblp.org/search/author/api?q={query}&format=json&h={limit}` ([DBLP API FAQ](https://dblp.org/faq/13501473)).
  - Canonical BibTeX Export: `GET https://dblp.org/rec/{key}.bib?param=0` (`param=0` standard BibTeX, `param=1` condensed, `param=2` with crossref proceedings entry) ([DBLP BibTeX Tool](https://github.com/tareqmahmood/dblp-bibtex/blob/main/README.md)).
- **2026 Anubis v1.27.0 Anti-Bot Challenge (`HTTP 202`) & Solution**:
  - In 2026, `dblp.org` (and `dblp.dagstuhl.de` / `dblp.uni-trier.de`) protects its API endpoints against cloud datacenter scraping using **Techaro Anubis `v1.27.0`**, returning `HTTP 202` HTML containing `<script id="anubis_challenge" type="application/json">{"rules":{"algorithm":"metarefresh","difficulty":1},"challenge":{"id":"...","randomData":"..."}}</script>`.
  - **How `acadsearch` Solves It Transparently**: When `_dblp_get_with_anubis` detects `HTTP 202` with `anubis_challenge`, it parses `challenge.id` and `challenge.randomData`, waits `1.08` seconds (`difficulty: 1`), and calls `GET https://dblp.org/.within.website/x/cmd/anubis/api/pass-challenge?id={id}&challenge={randomData}&redir={original_url}`. Anubis sets the `dblp_org-auth-...` cookie in the shared `httpx.Cookies` jar and redirects immediately to the `200 OK` JSON/BibTeX payload, allowing all subsequent DBLP requests in the session to succeed with zero latency.

---

### INSPIRE-HEP (`https://inspirehep.net/api`) & NASA ADS (`https://api.adsabs.harvard.edu/v1`)

- **INSPIRE-HEP REST API**:
  - Covers **1.7M+ records** in high-energy physics, quantum physics, general relativity, cosmology, and mathematics ([INSPIRE REST API](https://github.com/inspirehep/rest-api-doc/blob/master/README.md)).
  - Endpoints: `GET /api/literature?q={query}&sort=mostrecent|mostcited&size={n}&page={p}`, `GET /api/journals?q={query}`, `GET /api/conferences`, `GET /api/authors`, plus external ID resolution `GET /api/doi/{doi}`, `GET /api/arxiv/{arxiv_id}`, and `GET /api/orcid/{orcid}` ([INSPIRE REST API](https://github.com/inspirehep/rest-api-doc/blob/master/README.md)).
  - **Direct BibTeX & LaTeX Formats**: Append `?format=bibtex`, `?format=latex-eu`, or `?format=latex-us` (or pass `Accept: application/x-bibtex`) to any `/api/literature` search or record URL ([INSPIRE REST API](https://github.com/inspirehep/rest-api-doc/blob/master/README.md)).
  - **Rate Limit**: **15 requests per 5-second window (3 RPS)** per IP address ([INSPIRE REST API](https://github.com/inspirehep/rest-api-doc/blob/master/README.md)).
- **NASA ADS Developer API v1**:
  - Covers **16M+ astronomy, astrophysics, planetary science, and physics records** ([NASA ADS MCP](https://github.com/pipeworx-io/mcp-nasa-ads)).
  - Authenticate with `Authorization: Bearer $ADS_API_KEY` (5,000 requests/day).
  - Endpoints: `GET /v1/search/query?q={query}&fl=bibcode,title,author,year,pub,doi,abstract,citation_count&rows={n}`, `POST /v1/export/bibtex` (`{"bibcode": ["..."]}`), and `POST /v1/metrics` ([NASA ADS MCP](https://github.com/pipeworx-io/mcp-nasa-ads)).

---

## Tier 4: Commercial Bibliometric, Publisher TDM & Scientometric Databases

### Clarivate Web of Science (Starter API v1, Expanded API & JCR Journals API v1)

Clarivate provides three distinct REST APIs authenticated via the `X-ApiKey: $WOS_API_KEY` HTTP header ([Clarivate Developer Portal](https://developer.clarivate.com/apis)):

1. **Web of Science Starter API v1 (`https://api.clarivate.com/apis/wos-starter/v1`)**:
   - **Endpoints**: `GET /documents` and `GET /journals` ([Clarivate WoS Starter](https://developer.clarivate.com/apis/wos-starter), [Clarivate WoS Client](https://github.com/clarivate/wosstarter_python_client)).
   - **Supported Databases (`db`)**: `WOS` (Web of Science Core Collection), `WOK` (All Databases), `BIOABS` (Biological Abstracts), `BCI` (BIOSIS Citation Index), `MEDLINE`, `PPRN` (Preprint Citation Index), `DIIDW` (Derwent Innovations Index), `DRCI` (Data Citation Index).
   - **Advanced Query Field Tags (`q`)**: `TS=(...)` (Topic: title, abstract, author keywords, Keywords Plus), `TI=(...)` (Title), `AU=(...)` (Author), `AI=(...)` (ResearcherID / ORCID), `SO=(...)` (Source/Journal Title), `IS=(...)` (ISSN), `DO=(...)` (DOI), `PMID=(...)` (PubMed ID), `UT=(WOS:...)` (Accession Number), `PY=(2022-2026)` (Publication Year), `DT=(Article OR Review)` (Document Type), `OG=(...)` (Organization) ([Clarivate WoS Starter](https://developer.clarivate.com/apis/wos-starter)).
   - **Rate Limits**: 1–5 RPS, up to 5,000 requests/day on institutional starter subscriptions.
2. **Web of Science Journals API / Journal Citation Reports (JCR v1) (`https://api.clarivate.com/apis/wos-journals/v1`)**:
   - **Endpoints** ([Clarivate WoS Journals Client](https://github.com/clarivate/wosjournals-python-client/blob/main/docs/JournalsApi.md)):
     - `GET /journals?q={issn_or_title}&edition={SCIE|SSCI|AHCI|ESCI}&categoryCode={code}&jcrYear={year}&jif={range}&jifQuartile={Q1|Q2|Q3|Q4}&jifPercentile={0..100}&jci={range}&limit={1..50}&page={p}`
     - `GET /journals/{id}` (Journal metadata record by JCR abbreviated ID)
     - `GET /journals/{id}/reports/year/{year}` (Complete annual JCR metric profile: **Journal Impact Factor (`jif`)**, **5-Year JIF**, **Journal Citation Indicator (`jci`)**, **JIF Rank & Quartile (`Q1`–`Q4`)**, **JIF Percentile**, **Immediacy Index**, **Eigenfactor**, and **Article Influence Score**)
     - `GET /journals/{id}/citing/year/{year}` and `GET /journals/{id}/cited/year/{year}` (Journal-to-journal citation network).
3. **Web of Science Expanded API (`https://wos-api.clarivate.com/api/wos`)**:
   - **Endpoints**: `GET /api/wos` (`databaseId=WOS`, `usrQuery=TS=(...)`, `count=1..100`, `firstRecord=1`, `optionView=FR` for Full Record or `SR` for Short Record), `GET /api/wos/references` (cited references), `GET /api/wos/citing` (citing items), and `GET /api/wos/related` ([Clarivate WoS Expanded](https://developer.clarivate.com/apis/wos), [WoS Release Notes](https://clarivate.com/academia-government/release-notes/wos-apis/)).
   - **Plan Quotas**: Basic (2 RPS, 50,000 Full Records/yr), Intermediate (2 RPS, 250,000/yr), Advanced (3 RPS, 1,000,000/yr), Premium (5 RPS, 3,000,000/yr), or Essentials 1–3 (2–3 RPS, 100,000–1,000,000 Full Records/mo) ([Clarivate WoS Expanded](https://developer.clarivate.com/apis/wos)).

---

### Elsevier Scopus, ScienceDirect, Abstract Retrieval & Serial Title APIs (`https://api.elsevier.com`)

- **Authentication & Institutional Entitlements**:
  - Pass header `X-ELS-APIKey: $ELSEVIER_API_KEY` (and `X-ELS-Insttoken: $ELSEVIER_INSTTOKEN` when accessing subscriber-gated views such as `COMPLETE`, `REF`, and `FULL`) ([Elsevier Dev Portal](https://dev.elsevier.com/api_docs.html)).
  - **Zero-Key Fallback in `acadsearch`**: When `ELSEVIER_API_KEY` is not set, `acadsearch papers "<query>" --providers scopus` (or `elsevier` / `sciencedirect`) automatically queries Elsevier's official Crossref Member `78` catalog (**25,529,399+ ScienceDirect, Cell Press, and Lancet DOIs**) and enriches top results via OpenAlex's free (`$0.00`) singleton endpoint (`/works/https://doi.org/{doi}`).
- **Core Endpoints**:
  1. **Scopus Search API (`GET /content/search/scopus`)**:
     - Supports boolean field codes: `TITLE-ABS-KEY(...)`, `TITLE(...)`, `ABS(...)`, `KEY(...)`, `AUTH(...)`, `AFFIL(...)`, `SRCTITLE(...)`, `ISSN(...)`, `DOI(...)`, `PUBYEAR > 2022`, `SUBJAREA(COMP OR ENGI)`, `FUND-SPONSOR(...)`, `OPENACCESS(1)` ([Elsevier Dev Portal](https://dev.elsevier.com/api_docs.html)).
     - Views: `STANDARD` (default metadata + `citedby-count`) and `COMPLETE` (adds full abstract, author affiliations, and funding metadata; requires subscriber entitlement). Weekly quota: 20,000 requests/week.
  2. **Scopus Abstract Retrieval API (`GET /content/abstract/...`)**:
     - Routes: `/content/abstract/doi/{doi}`, `/content/abstract/scopus_id/{scopus_id}`, `/content/abstract/eid/{eid}`, and `/content/abstract/pubmed_id/{pmid}` ([Elsevier Abstract Retrieval](https://dev.elsevier.com/documentation/AbstractRetrievalAPI.wadl), [Scopus Views](https://dev.elsevier.com/sc_abstract_retrieval_views.html)).
     - Views: `BASIC`, `META`, `META_ABS` (abstract + metadata), `REF` (complete bibliography references), `FULL` (complete Scopus record).
     - Content Negotiation: Supports `Accept: application/json`, `Accept: text/xml`, `Accept: application/x-bibtex`, and `Accept: application/x-research-info-systems`.
  3. **ScienceDirect Search V2 & Full-Text Article Retrieval API (`GET /content/article/doi/{doi}`)**:
     - Search: `GET/PUT https://api.elsevier.com/content/search/sciencedirect` ([ScienceDirect Swagger](https://dev.elsevier.com/elsdoc/sciencedirect)).
     - Full-Text Retrieval: `GET https://api.elsevier.com/content/article/doi/{doi}?view=FULL` or `GET https://api.elsevier.com/content/article/pii/{pii}?view=FULL` with `Accept: application/json` or `Accept: text/xml` ([Elsevier Article Retrieval](https://dev.elsevier.com/documentation/ArticleRetrievalAPI.wadl), [Elsevier TDM Guide](https://dev.elsevier.com/tecdoc_text_mining.html)). Returns the complete full-text body (`originalText` / XML `<ce:sections>`) and embedded media object references.
  4. **Elsevier Serial Title API (`GET /content/serial/title/issn/{issn}?view=ENHANCED`)**:
     - Returns official **CiteScore** (`citeScoreYearInfoList.citeScoreCurrentMetric`), **CiteScore Tracker**, **SCImago Journal Rank (SJR)** (`SJRList.SJR`), **Source Normalized Impact per Paper (SNIP)** (`SNIPList.SNIP`), and subject area percentiles ([Scopus APIs Spec](https://nonprod-devportal.elsevier.com/sc_api_spec.html)).

---

### Wiley Online Library TDM API v1 (`https://api.wiley.com`) & Crossref Member `311`

- **Wiley Text and Data Mining (TDM) Full-Text PDF API**:
  - **Endpoint**: `GET https://api.wiley.com/onlinelibrary/tdm/v1/articles/{url_encoded_doi}` (where `/` in the DOI is URL-encoded as `%2F`, e.g., `10.1002%2Fnet.22207`) ([Wiley TDM Guide](https://ua-libraries-research-data-services.github.io/UALIB_ScholarlyAPI_Cookbook/python/wiley-tdm.html), [Wiley TDM Client](https://github.com/WileyLabs/tdm-client)).
  - **Authentication**: Header `Wiley-TDM-Client-Token: $WILEY_TDM_TOKEN` (or environment variable `TDM_API_TOKEN` used by the official `pip install wiley-tdm` package) ([Wiley TDM Client](https://github.com/WileyLabs/tdm-client)).
  - **Entitlement & Rate Limits**: Streams the complete publisher PDF (`application/pdf`) at up to **3 requests/second**; paywalled Wiley articles require institutional IP recognition alongside the TDM token, whereas Open Access Wiley articles (`Battery Energy`, *Advanced Science*, etc.) are also directly accessible via `https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}` ([Wiley Lib Info](https://onlinelibrary.wiley.com/library-info/resources/text-and-datamining)).
- **Wiley Article & Journal Discovery (12,237,680+ DOIs)**:
  - Because Wiley's TDM API only accepts known DOIs, article and journal search across Wiley's 1,600+ journals (*Advanced Materials*, *Angewandte Chemie*, *WIREs*, *Cochrane Database of Systematic Reviews*, *Journal of Finance*) is performed via Wiley's official Crossref Member ID **`311`**:
    `GET https://api.crossref.org/v1/members/311/works?query.bibliographic={query}&filter=from-pub-date:{YYYY},issn:{ISSN}&rows={n}&mailto={email}`
  - In `acadsearch`, passing `--providers wiley` queries Crossref Member `311`, automatically enriches top results via OpenAlex's `$0.00` singleton endpoint (`/works/https://doi.org/{doi}`) to attach full reconstructed abstracts, citation counts, and Open Access PDF links, and uses `extract_wiley_tdm_pdf_context` when `WILEY_TDM_TOKEN` is present.

---

### Springer Nature, IEEE Xplore, Major Academic Publishers & Dimensions / Lens

- **Springer Nature API (`https://api.springernature.com`)**:
  - **Meta v2 API**: `GET /meta/v2/json?q=title:"..." AND onlinedatefrom:2024-01-01&p=10&api_key=$SPRINGER_API_KEY` (16M+ Nature, Springer, Palgrave, and BMC documents) ([Springer Meta API](https://dev.springernature.com/docs/api-endpoints/meta-api/)).
  - **Open Access JATS API**: `GET /openaccess/jats?q=doi:{doi}&api_key=$SPRINGER_API_KEY` returns **full-text JATS XML** (structured `<sec>` sections, paragraphs, equations, tables) for 1.5M+ open-access Springer Nature articles ([Springer OA API](https://dev.springernature.com/docs/api-endpoints/open-access/)).
  - **Full-Text TDM API (2026 Migration)**: On **August 7, 2026**, Springer Nature retired `spdi.public.springernature.app`; subscriber full-text TDM JATS XML requests now use `GET https://api.springernature.com/xmldata/jats?q=doi:{doi}&api_key=YOUR_API_KEY/YOUR-API-METRIC` ([Springer Full Text API](https://dev.springernature.com/docs/api-endpoints/fulltext-api/)).
  - **Zero-Key Fallback**: Crossref Member **`297`** (**19,060,623+ Springer Nature DOIs**) + OpenAlex singleton enrichment.
- **IEEE Xplore Metadata & Full-Text API v1 (`https://ieeexploreapi.ieee.org/api/v1/search/articles`)**:
  - Query parameters: `querytext` (supports `AND`, `OR`, `NOT`, `NEAR/#`, `ONEAR/#`), `article_title`, `author`, `isbn`, `issn`, `doi`, `publication_title`, `content_type` (`Journals`, `Conferences`, `Standards`, `Books`), `open_access` (`True`), `start_year`, `end_year`, `max_records` (up to 200), `apikey` ([IEEE Xplore API](https://developer.ieee.org/docs/read/Searching_the_IEEE_Xplore_Metadata_API), [IEEE Boolean](https://developer.ieee.org/docs/read/metadata_api_details/Leveraging_Boolean_Logic)).
  - **Zero-Key Fallback**: Crossref Member **`263`** (**6,248,530+ IEEE DOIs**) + OpenAlex singleton enrichment.
- **Major Academic Society & University Press Publishers ("etc.")**:
  - `acadsearch` supports direct publisher-scoped search (`--providers <key>`) across **16 major academic publishers** using their verified Crossref Member IDs plus OpenAlex `$0.00` singleton enrichment and Unpaywall OA PDF resolution:
    - `elsevier` / `scopus` / `sciencedirect` (Member `78` — **25,529,399 DOIs**)
    - `springer_nature` / `springer` / `nature` (Member `297` — **19,060,623 DOIs**)
    - `wiley` (Member `311` — **12,237,680 DOIs**)
    - `taylor_francis` (Member `301` — **8,352,307 DOIs**, Informa UK / Taylor & Francis / Routledge / CRC Press)
    - `oup` / `oxford` (Member `286` — **7,604,556 DOIs**, Oxford University Press)
    - `ieee` / `ieee_xplore` (Member `263` — **6,248,530 DOIs**, IEEE)
    - `sage` (Member `179` — **3,774,476 DOIs**, SAGE Publications)
    - `cup` / `cambridge` (Member `56` — **2,570,664 DOIs**, Cambridge University Press)
    - `mdpi` (Member `1968` — **2,246,637 DOIs**, MDPI AG, 100% Gold OA)
    - `acs` (Member `316` — **2,240,477 DOIs**, American Chemical Society)
    - `iop` (Member `266` — **1,301,427 DOIs**, IOP Publishing)
    - `rsc` (Member `292` — **1,144,191 DOIs**, Royal Society of Chemistry)
    - `frontiers` (Member `1965` — **849,113 DOIs**, Frontiers Media SA, 100% Gold OA)
    - `aps` (Member `16` — **819,198 DOIs**, American Physical Society + `http://harvest.aps.org/v2/journals/articles`)
    - `acm` (Member `320` — **779,656 DOIs**, Association for Computing Machinery)
    - `plos` (Member `340` — **418,626 DOIs**, Public Library of Science + `https://api.plos.org/search?q=...&wt=json`)
- **Dimensions (`https://app.dimensions.ai/api/dsl/v2`) & The Lens (`https://api.lens.org/scholarly/search`)**:
  - Link 140M+ scholarly articles directly to citing patents, clinical trials, policy documents, and grant awards; Dimensions enforces **30 RPM per IP** and provides an official **Dimensions Analytics MCP** server ([Dimensions DSL](https://docs.dimensions.ai/dsl/api.html), [Lens API](https://about.lens.org/lens-apis/)).

---

## Tier 5: AI-Native Academic Search & Full-Text PDF Context Pipeline

### Consensus, scite, Elicit v2 & FutureHouse PaperQA2

1. **Consensus (`https://mcp.consensus.app/mcp`)**:
   - Hosted Streamable HTTP MCP server exposing `search` with first-class clinical and scientometric filters: `study_types` (`rct`, `meta-analysis`, `systematic review`, `literature review`, `case report`, `non-rct experimental`, `non-rct observational study`, `non-rct in vitro`, `animal`), `sjr_max` (`1`=Q1 through `4`=Q4 journal quartile), `sample_size_min`, `human`, `medical_mode`, `exclude_preprints`, `year_min`, and `year_max` (rate limit: **1 RPS**) ([Consensus MCP Docs](https://docs.consensus.app/docs/mcp)).
2. **scite (`https://api.scite.ai/mcp`)**:
   - Hosted Streamable HTTP MCP server (`POST /mcp` JSON-RPC 2.0, `Authorization: Bearer scite_...`) exposing **25 tools**: `search_literature` (returning publisher-indexed **Smart Citations** classified as **supporting**, **contrasting**, or **mentioning** with exact in-text citation sentences), 17 biomedical/regulatory evidence tools (`search_clinical_trials`, `search_patents`, `search_grants`, `search_device510k`, `search_faers`, `search_maude`, `search_mhra`, `search_drugs`), and 7 collection tools ([scite MCP Overview](https://docs.scite.ai/mcp/overview), [scite MCP Tools](https://docs.scite.ai/mcp/tools/overview)).
3. **Elicit v2 REST API (`https://elicit.com/api/v2`) & MCP (`https://elicit.com/api/mcp`)**:
   - Synchronous paper search (`POST /api/v2/search/papers`, retracted papers excluded by default) and clinical trial search (`POST /api/v2/search/trials`), plus asynchronous systematic review sessions (`POST /api/v2/sessions/systematic-reviews`) and cited report generation (`POST /api/v2/sessions/reports`). **Guardrail**: Strictly enforce `<100 RPM` per IP address (including polling) to avoid Elicit's automatic 5-minute IP ban ([Elicit API Ref](https://docs.elicit.com/llms.txt)).
4. **FutureHouse PaperQA2 (`pip install paper-qa>=5` & `futurehouse-mcp`)**:
   - Exposes `Crow` (fast cited search), `Falcon` (deep literature review), `Owl` (precedent verification), and `Phoenix` (chemistry synthesis), plus local multi-step PDF RAG with metadata-aware reranking ([FutureHouse Launch](https://www.futurehouse.org/news/launching-futurehouse-platform-ai-agents), [PaperQA2 Repo](https://github.com/Future-House/paper-qa?tab=readme-ov-file)).

---

### The 4-Tier Full-Text & PDF Context Pipeline (`acadsearch context`)

To give an agent complete paper context (abstract, TLDR, section headings, mathematical equations, experimental tables, and method details) without overflowing the prompt window or corrupting multi-column PDF text, `acadsearch` executes a deterministic **4-Tier Full-Text Cascade**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Input: DOI / arXiv ID / PMID / PMCID / Paper Title + Optional focus_query  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 0: Multi-Provider Metadata, Reconstructed Abstract, TLDR & BibTeX      │
│ (OpenAlex Singleton/Search + Semantic Scholar + Crossref + Europe PMC +     │
│  arXiv + DBLP + Unpaywall Legal OA PDF Resolution)                          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Tier 1: Semantic Scholar Full-Text Snippet Search (/graph/v1/snippet/search)│
│ -> Retrieves ~500-word body passages ranked against focus_query             │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Tier 2: Native arXiv LaTeXML HTML (arxiv.org/html/{id} & ar5iv.labs.arxiv)  │
│ -> Extracts structured <section class="ltx_section"> headings, paragraphs,  │
│    tables, and inline LaTeX equations (if arxiv_id is present)              │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Tier 3: NCBI PMC BioC JSON (pmcoa.cgi/BioC_json & PubTator3 biocjson)       │
│ -> Extracts segmented TITLE, ABSTRACT, INTRO, METHODS, RESULTS, DISCUSS,    │
│    FIG, and TABLE passages (if PMCID or PMID is present)                    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Tier 4: Direct Open-Access PDF Extraction (Unpaywall/OA pdf_url + pypdf)    │
│ -> Downloads OA PDF (<=25 MB), extracts page text, and ranks sections by    │
│    focus_query keyword overlap when structured HTML/BioC is unavailable     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## `acadsearch` Unified Implementation Reference

The complete implementation lives in `/home/user/workspace/academic-search-api` and is packaged as an installable Python distribution (`pip install -e .`).

### Package Layout
```text
academic-search-api/
├── pyproject.toml                       # Installable package defining `acadsearch` & `acadsearch-mcp`
├── README.md                            # Quickstart and architecture guide
├── openapi.json                         # Exported OpenAPI 3.1.0 specification
├── mcp_config.example.json              # Ready-to-use MCP client configuration
├── acadsearch/
│   ├── __init__.py                      # Exports AcademicSearchClient & Pydantic models
│   ├── models.py                        # PaperRecord, JournalRecord, PaperContextResult, CitationGraphResult
│   ├── utils.py                         # Identifier classifier, OpenAlex abstract reconstructor, BibTeX synthesizer, deduplicator
│   ├── client.py                        # Async & sync AcademicSearchClient orchestrator
│   ├── cli.py                           # `acadsearch` CLI (papers, journals, paper, bibtex, context, citations, databases, serve, mcp)
│   ├── server.py                        # FastAPI HTTP REST API + Streamable HTTP `/mcp` endpoint
│   ├── mcp_server.py                    # JSON-RPC 2.0 Model Context Protocol (MCP) server (7 tools)
│   └── providers/
│       ├── openalex.py                  # OpenAlex /works, /sources, citation graphs & $0.00 singleton enrichment
│       ├── semantic_scholar.py          # Semantic Scholar /paper/search, /search/bulk fallback & /snippet/search
│       ├── crossref.py                  # Crossref /v1/works, /v1/journals & universal doi.org BibTeX negotiation
│       ├── arxiv.py                     # arXiv Atom XML search, /bibtex/{id} & arXiv HTML / ar5iv section parser
│       ├── pubmed_epmc.py               # Europe PMC JSON, NCBI PMC BioC JSON & PubTator 3.0 full-text extractor
│       ├── doaj_dblp_inspire.py         # DOAJ v4, DBLP (with Anubis v1.27.0 solver), INSPIRE-HEP, Unpaywall, OpenCitations, pypdf
│       └── keyed_enterprise.py          # 24+ database registry catalog, CORE v3 & Elsevier Serial Title CiteScore/SJR/SNIP
├── skills/
│   └── academic-search/
│       ├── SKILL.md                     # Agent Skill entrypoint and routing table
│       └── references/                  # 5 deep reference manuals for direct API calls
└── tests/
    └── test_acadsearch.py               # Automated unit, REST API, and MCP protocol test suite
```

### MCP Server Tool Specifications (`acadsearch-mcp`)

| Tool Name | Input Arguments | Returned Payload |
| :--- | :--- | :--- |
| `academic_search_papers` | `query` (req), `providers`, `year_min`, `year_max`, `open_access_only`, `venue`, `min_citations`, `limit`, `sort`, `include_bibtex` | `SearchPapersResponse` with deduplicated `PaperRecord` list (`title`, `doi`, `arxiv_id`, `pmid`, `pmcid`, `openalex_id`, `authors`, `journal`, `abstract`, `tldr`, `citation_count`, `pdf_url`, `bibtex`, `source_providers`) |
| `academic_search_journals` | `query`, `issn`, `open_access_only`, `limit` | `SearchJournalsResponse` with `JournalRecord` list (`title`, `issn_l`, `issns`, `publisher`, `is_oa`, `is_in_doaj`, `apc_usd`, `metrics.two_year_mean_citedness`, `metrics.h_index`, `metrics.i10_index`, `metrics.citescore`, `metrics.sjr`, `topics`) |
| `academic_get_paper` | `identifier` (DOI, arXiv ID, PMID, PMCID, OpenAlex ID, or title), `include_bibtex` | Single merged `PaperRecord` enriched across OpenAlex, Semantic Scholar, Crossref, arXiv, Europe PMC, and Unpaywall |
| `academic_get_bibtex` | `identifier` (DOI, arXiv ID, DBLP key, PMID, or title) | Official or synthesized BibTeX string |
| `academic_get_pdf_context` | `identifier` (req), `focus_query` (opt), `max_chars` (default `12000`) | `PaperContextResult` containing `abstract`, `tldr`, `bibtex`, `pdf_url`, structured `sections` (`heading`, `content`), ranked 500-word `snippets`, and `full_text_excerpt` |
| `academic_get_citations` | `identifier` (req), `direction` (`both`, `citing`, `references`), `limit` | `CitationGraphResult` with incoming `citing_papers` and outgoing `references` |
| `academic_list_databases` | `{}` | Catalog of all 24+ supported databases, base URLs, auth modes, rate limits, and capabilities |
