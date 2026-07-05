"""Adapters that map a viparse :class:`~viparse.model.Document` onto RAG-framework types.

Each adapter lazily imports its framework, so importing this package pulls in neither
LangChain nor LlamaIndex — install ``viparse[langchain]`` / ``viparse[llamaindex]`` to use one.
"""

from __future__ import annotations

from viparse.integrations.langchain import to_langchain_documents
from viparse.integrations.llamaindex import to_llamaindex_documents

__all__ = ["to_langchain_documents", "to_llamaindex_documents"]
