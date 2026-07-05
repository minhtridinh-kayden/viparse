# Examples

Runnable examples of using viparse in a RAG pipeline.

| Example | What it shows |
| --- | --- |
| [`rag_pipeline.py`](rag_pipeline.py) | A Vietnamese document (including legacy TCVN3/VNI/VISCII fonts) → viparse `load(..., chunk=...)` → LangChain `Document`s → a FAISS vector index → Vietnamese similarity search. |

These scripts import optional, heavy dependencies (embedding models, a vector store) and are
**not** run in CI — they are documentation of the intended end-to-end flow. Install the extras
named at the top of each file to run it locally.

The LlamaIndex path is symmetric: swap `to_langchain_documents` for `to_llamaindex_documents`
and feed the returned `Document`s into a LlamaIndex `VectorStoreIndex`.
