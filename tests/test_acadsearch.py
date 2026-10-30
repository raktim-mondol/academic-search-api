from __future__ import annotations
import asyncio
from fastapi.testclient import TestClient
from acadsearch.client import AcademicSearchClient
from acadsearch.mcp_server import handle_jsonrpc_message
from acadsearch.models import AuthorRecord, JournalSummary, PaperRecord
from acadsearch.server import app
from acadsearch.utils import (
    classify_identifier,
    deduplicate_and_merge_papers,
    reconstruct_abstract,
    synthesize_bibtex,
)


def test_identifier_classification() -> None:
    assert classify_identifier("https://doi.org/10.1038/nature14539") == ("doi", "10.1038/nature14539")
    assert classify_identifier("arXiv:1706.03762v5") == ("arxiv", "1706.03762")
    assert classify_identifier("PMC11223843") == ("pmcid", "PMC11223843")
    assert classify_identifier("PMID:29355051") == ("pmid", "29355051")
    assert classify_identifier("W2741809807") == ("openalex_work", "W2741809807")
    assert classify_identifier("1476-4687") == ("issn", "1476-4687")
    assert classify_identifier("conf/nips/VaswaniSPUJGKP17") == ("dblp", "conf/nips/VaswaniSPUJGKP17")


def test_reconstruct_abstract_and_bibtex() -> None:
    inv = {"Deep": [0], "learning": [1], "transforms": [2], "science.": [3]}
    assert reconstruct_abstract(inv) == "Deep learning transforms science."

    p1 = PaperRecord(
        id="doi:10.1038/nature14539",
        title="Deep learning",
        doi="10.1038/nature14539",
        authors=[AuthorRecord(name="Yann LeCun"), AuthorRecord(name="Geoffrey Hinton")],
        year=2015,
        journal=JournalSummary(name="Nature"),
        volume="521",
        pages="436-444",
        source_providers=["crossref"],
    )
    bib = synthesize_bibtex(p1)
    assert "@article{lecun2015deep," in bib
    assert "doi = {10.1038/nature14539}" in bib

    p2 = PaperRecord(
        id="openalex:W123",
        title="Deep learning",
        doi="10.1038/nature14539",
        abstract="Deep learning allows computational models...",
        citation_count=95000,
        is_oa=True,
        pdf_url="https://example.org/deep.pdf",
        source_providers=["openalex"],
    )
    merged = deduplicate_and_merge_papers([p1, p2])
    assert len(merged) == 1
    assert merged[0].abstract == "Deep learning allows computational models..."
    assert merged[0].citation_count == 95000
    assert set(merged[0].source_providers) == {"crossref", "openalex"}


def test_fastapi_and_mcp_endpoints() -> None:
    tc = TestClient(app)
    r_health = tc.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "ok"

    r_dbs = tc.get("/v1/databases")
    assert r_dbs.status_code == 200
    assert r_dbs.json()["count"] >= 24

    r_bib = tc.get("/v1/bibtex", params={"id": "10.1038/nature14539"})
    assert r_bib.status_code == 200
    assert "@article" in r_bib.text

    r_mcp = tc.post("/mcp", json={"jsonrpc": "2.0", "id": 99, "method": "tools/list"})
    assert r_mcp.status_code == 200
    tools = r_mcp.json()["result"]["tools"]
    assert len(tools) == 7


if __name__ == "__main__":
    test_identifier_classification()
    test_reconstruct_abstract_and_bibtex()
    test_fastapi_and_mcp_endpoints()
    print("All unit, REST API, and MCP protocol tests passed!")
