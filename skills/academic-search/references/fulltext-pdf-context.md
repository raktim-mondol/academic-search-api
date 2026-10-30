# Full-Text & PDF Context Extraction Pipeline for Agents

Downloading raw 30-page academic PDFs and dumping raw OCR text into an agent's prompt wastes 30,000+ tokens and mangles LaTeX equations and multi-column tables. Instead, use the **4-Tier Full-Text Context Cascade** implemented in `acadsearch context "<id>"` (`client.get_pdf_context()`).

---

## The 4-Tier Full-Text Context Cascade

### Tier 1: Targeted 500-Word Body Passages (`Semantic Scholar /snippet/search`)
- **When to use**: When the agent wants to answer a specific technical question (e.g., hyperparameter settings, dataset splits, ablation results, theorem statements) across one or more papers.
- **Endpoint**: `GET https://api.semanticscholar.org/graph/v1/snippet/search?query={focus_query}&paperIds={s2_id}&limit=10`
- **Output**: Pre-chunked ~500-word excerpts from the paper's body text, tagged with `snippet.section` (`Introduction`, `Methodology`, `Experiments`, `Conclusion`) and character offsets.

### Tier 2: Native LaTeXML HTML (`arXiv HTML` & `ar5iv`)
- **When to use**: Any paper with an `arxiv_id` (Computer Science, Mathematics, Physics, Quantitative Biology, Statistics, Quantitative Finance, Economics).
- **Endpoints**:
  1. `https://arxiv.org/html/{arxiv_id}` (Official arXiv LaTeXML HTML)
  2. `https://ar5iv.labs.arxiv.org/html/{arxiv_id}` (ar5iv HTML5 mirror covering 2M+ historical arXiv papers)
- **Why it beats PDF parsing**: Preserves exact `<section class="ltx_section">` hierarchy, `<table class="ltx_tabular">` structures, and inline LaTeX math annotations (`<annotation encoding="application/x-tex">`) with zero column-wrapping corruption.

### Tier 3: Structured Biomedical Passages (`NCBI PMC BioC JSON` & `PubTator 3.0`)
- **When to use**: Any paper with a `PMCID` (`PMC...`) or `PMID` in the PubMed Central Open Access subset (6.5M+ biomedical and life-science papers).
- **Endpoints**:
  1. `https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/{pmcid_or_pmid}/unicode`
  2. `https://www.ncbi.nlm.nih.gov/research/pubtator3-api/publications/export/biocjson?pmids={pmid}&full=true`
  3. `https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML`
- **Why it beats PDF parsing**: Returns pre-segmented JSON passages labeled by `infons.section_type`: `TITLE`, `ABSTRACT`, `INTRO`, `METHODS`, `RESULTS`, `FIG`, `TABLE`, `DISCUSS`, `CONCL`, allowing the agent to skip `REF` (bibliography) and `ACK_FUND` boilerplate automatically.

### Tier 4: Legal Open-Access PDF Resolution + Windowed Extraction (`Unpaywall` + `pypdf` / `Jina Reader`)
- **When to use**: Published journal articles without arXiv HTML or PMC BioC records.
- **Step 1 (Resolve Legal OA PDF URL)**:
  - Check OpenAlex `best_oa_location.pdf_url`
  - Check Semantic Scholar `openAccessPdf.url`
  - Query Unpaywall `GET https://api.unpaywall.org/v2/{doi}?email=agent@example.org` -> `best_oa_location.url_for_pdf`
- **Step 2 (Extract Section/Query Windows)**:
  - Local Python: `acadsearch context "<doi>" --query "<focus_keywords>"` downloads the PDF (up to 25 MB), extracts page text via `pypdf`, and ranks pages/passages by keyword overlap with `focus_query`.
  - Remote Markdown Reader fallback: `curl -s "https://r.jina.ai/{pdf_url}"` converts remote PDFs into clean Markdown using Jina Reader (`readerlm-v2` / `jina-ocr-v1`).
