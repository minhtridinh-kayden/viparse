"""LlamaIndex adapter: viparse :class:`Document` → ``llama_index.core.schema.Document``.

LlamaIndex is an optional, lazily-imported dependency (``viparse[llamaindex]``); importing
this module never imports LlamaIndex, so ``core`` stays light.
"""

from __future__ import annotations

from typing import Any

from viparse.errors import MissingDependency
from viparse.integrations._common import document_records
from viparse.model import Document


def to_llamaindex_documents(document: Document) -> list[Any]:
    """Convert ``document`` to a list of LlamaIndex ``Document`` objects.

    Emits one LlamaIndex ``Document`` per viparse chunk when the document is chunked, else a
    single one for the whole document. The viparse text maps to ``text`` and the flattened
    provenance to ``metadata``. Raises :class:`~viparse.errors.MissingDependency` if
    LlamaIndex is not installed.
    """
    li_document = _llamaindex_document_class()
    return [
        li_document(text=text, metadata=metadata) for text, metadata in document_records(document)
    ]


def _llamaindex_document_class() -> Any:
    try:
        from llama_index.core.schema import Document as LlamaIndexDocument
    except ImportError as exc:
        raise MissingDependency(
            "LlamaIndex is required for this integration; install viparse[llamaindex]"
        ) from exc
    return LlamaIndexDocument
