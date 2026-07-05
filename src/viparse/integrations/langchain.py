"""LangChain adapter: viparse :class:`Document` → ``langchain_core.documents.Document``.

LangChain is an optional, lazily-imported dependency (``viparse[langchain]``); importing
this module never imports LangChain, so ``core`` stays light.
"""

from __future__ import annotations

from typing import Any

from viparse.errors import MissingDependency
from viparse.integrations._common import document_records
from viparse.model import Document


def to_langchain_documents(document: Document) -> list[Any]:
    """Convert ``document`` to a list of LangChain ``Document`` objects.

    Emits one LangChain ``Document`` per viparse chunk when the document is chunked, else a
    single one for the whole document. The viparse text maps to ``page_content`` and the
    flattened provenance to ``metadata``. Raises :class:`~viparse.errors.MissingDependency`
    if LangChain is not installed.
    """
    lc_document = _langchain_document_class()
    return [
        lc_document(page_content=text, metadata=metadata)
        for text, metadata in document_records(document)
    ]


def _langchain_document_class() -> Any:
    try:
        from langchain_core.documents import Document as LangChainDocument
    except ImportError as exc:
        raise MissingDependency(
            "LangChain is required for this integration; install viparse[langchain]"
        ) from exc
    return LangChainDocument
