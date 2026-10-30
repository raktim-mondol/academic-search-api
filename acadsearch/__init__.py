from .client import AcademicSearchClient
from .models import (
    AuthorRecord,
    CitationEdge,
    CitationGraphResult,
    ContextSnippet,
    JournalMetrics,
    JournalRecord,
    JournalSummary,
    PaperContextResult,
    PaperRecord,
    SearchJournalsResponse,
    SearchPapersResponse,
)

__all__ = [
    "AcademicSearchClient",
    "AuthorRecord",
    "CitationEdge",
    "CitationGraphResult",
    "ContextSnippet",
    "JournalMetrics",
    "JournalRecord",
    "JournalSummary",
    "PaperContextResult",
    "PaperRecord",
    "SearchJournalsResponse",
    "SearchPapersResponse",
]
__version__ = "1.0.0"
