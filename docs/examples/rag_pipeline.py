"""End-to-end example: a Vietnamese document → viparse → a vector database (SPEC-4 E4.4).

This is the whole point of viparse: take a real-world Vietnamese file — including one saved
in a legacy TCVN3 / VNI / VISCII font — and get clean, Unicode-**NFC**, retrieval-sized chunks
that drop straight into a RAG stack, with the diacritics correct so embeddings and search work.

Run it with the integration extras installed::

    pip install "viparse[office,langchain]" langchain-community langchain-huggingface faiss-cpu
    python docs/examples/rag_pipeline.py path/to/bao-cao.docx

The example is intentionally dependency-light in what it *asserts*: viparse itself needs no
LLM. Swap FAISS / the embedding model for whatever your stack already uses.
"""

from __future__ import annotations

import sys

from viparse import ChunkOptions, load, to_langchain_documents


def build_index(path: str) -> None:
    # 1. Parse + normalize + chunk in one call. `chunk=` turns on retrieval-sized splitting;
    #    the output is always Unicode NFC, so "Việt" is one consistent string, never "Viẹt"
    #    or garbled legacy bytes. Default output is markdown (tables and headings preserved).
    (document,) = load(path, chunk=ChunkOptions(max_tokens=256, overlap_tokens=32))
    print(f"parsed {path}: {len(document.chunks)} chunks, engine={document.metadata.engine}")

    # 2. Map viparse chunks onto LangChain Documents — one per chunk, each carrying the source
    #    provenance (source, page/sheet, section, chunk_index) in `.metadata` for citations.
    lc_documents = to_langchain_documents(document)

    # 3. Embed and index. Any embedding model / vector store works; this uses FAISS locally.
    from langchain_community.vectorstores import FAISS
    from langchain_huggingface import HuggingFaceEmbeddings

    # A multilingual model so Vietnamese is embedded well.
    embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-small")
    store = FAISS.from_documents(lc_documents, embeddings)

    # 4. Retrieve. The query is Vietnamese; because both sides are NFC, matching is reliable.
    hits = store.similarity_search("Nội dung chính của báo cáo là gì?", k=3)
    for rank, hit in enumerate(hits, start=1):
        section = hit.metadata.get("section") or "(no section)"
        print(f"\n#{rank} [section={section} chunk={hit.metadata.get('chunk_index')}]")
        print(hit.page_content[:300])


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python docs/examples/rag_pipeline.py <document>")
    build_index(sys.argv[1])


if __name__ == "__main__":
    main()
