"""Retrieval-Augmented Generation over the datasheet knowledge base.

Pipeline: Markdown datasheet excerpts -> section-aware chunking -> local ONNX
embeddings (all-MiniLM-L6-v2 via Chroma, no API key, no PyTorch) -> persistent
Chroma collection -> metadata-filtered retrieval with citations.

Every chunk keeps: source file, title, section, page, source URL, manufacturer,
component ids and part numbers, so research agents can cite exactly where a
fact came from.
"""

from __future__ import annotations

import hashlib
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path

from hermes.config import DATA_DIR, DATASHEETS_DIR

COLLECTION = "hermes-datasheets"
_PAGE_RE = re.compile(r"^Page:\s*(\S+)\s*$", re.MULTILINE)
_COMPONENTS_RE = re.compile(r"^Components:\s*(.+)$", re.MULTILINE)
_SOURCE_URL_RE = re.compile(r"Sources?:\s*(https?://\S+)")


@dataclass
class Document:
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class Hit:
    text: str
    score: float  # cosine similarity, higher is better
    metadata: dict

    def citation(self) -> str:
        m = self.metadata
        page = "" if m.get("page") in (None, "", "web", "N/A") else f", page {m['page']}"
        return f"{m.get('source')} [{m.get('section')}]{page} <{m.get('source_url')}>"


# ---- 1. ingestion -----------------------------------------------------------------


def _parse_front_matter(raw: str) -> tuple[dict, str]:
    if not raw.startswith("---"):
        return {}, raw
    _, header, body = raw.split("---", 2)
    meta = {}
    for line in header.strip().splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, body


def load_documents(directory: Path = DATASHEETS_DIR) -> list[Document]:
    """Load every Markdown datasheet excerpt with its front-matter metadata."""
    docs = []
    for path in sorted(directory.glob("*.md")):
        meta, body = _parse_front_matter(path.read_text(encoding="utf-8"))
        meta["source"] = path.name
        docs.append(Document(text=body.strip(), metadata=meta))
    return docs


# ---- 2. chunking ----------------------------------------------------------------------


def chunk_documents(docs: list[Document], chunk_size: int = 900, chunk_overlap: int = 120) -> list[Document]:
    """Split on '## ' sections first (keeps tables and notes together), then by size.

    Section-level ``Page: N``, ``Components: ...`` and ``Source: <url>`` lines override
    the document-level metadata, so citations and component filters stay precise.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap,
                                              separators=["\n\n", "\n", ". ", " "])
    chunks: list[Document] = []
    for doc in docs:
        sections = re.split(r"(?m)^## ", doc.text)
        for section in sections:
            section = section.strip()
            if not section or section.startswith("# "):
                continue  # skip the document title block
            heading, _, content = section.partition("\n")
            page_match = _PAGE_RE.search(content)
            page = page_match.group(1) if page_match else doc.metadata.get("page", "web")
            comp_match = _COMPONENTS_RE.search(content)
            component_ids = comp_match.group(1).strip() if comp_match else doc.metadata.get("component_ids", "")
            url_match = _SOURCE_URL_RE.search(content)
            source_url = url_match.group(1).rstrip(".") if url_match else doc.metadata.get("source_url", "")
            content = _COMPONENTS_RE.sub("", _PAGE_RE.sub("", content)).strip()
            for i, piece in enumerate(splitter.split_text(content)):
                meta = {
                    "source": doc.metadata.get("source", ""),
                    "title": doc.metadata.get("title", ""),
                    "section": heading.strip(),
                    "page": page,
                    "source_url": source_url,
                    "manufacturer": doc.metadata.get("manufacturer", ""),
                    "component_ids": component_ids,
                    "part_numbers": doc.metadata.get("part_numbers", ""),
                    "retrieved_on": doc.metadata.get("retrieved_on", ""),
                    "chunk": i,
                }
                # One boolean flag per component id enables exact metadata filtering.
                for cid in filter(None, (c.strip() for c in meta["component_ids"].split(","))):
                    meta[f"cid:{cid}"] = True
                # Prefix with title + section so each chunk is self-describing for the embedder.
                text = f"{meta['title']} - {heading.strip()}\n{piece}"
                chunks.append(Document(text=text, metadata=meta))
    return chunks


def corpus_hash(directory: Path = DATASHEETS_DIR) -> str:
    h = hashlib.sha256()
    for path in sorted(directory.glob("*.md")):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()[:16]


# ---- 3-4. embeddings + vector store -------------------------------------------------------


class DatasheetIndex:
    """Persistent Chroma collection with local embeddings. Rebuilt only when the corpus changes."""

    def __init__(self, persist_dir: Path | None = None, directory: Path = DATASHEETS_DIR):
        import chromadb
        from chromadb.config import Settings
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

        self.directory = directory
        self.persist_dir = persist_dir or DATA_DIR / "chroma"
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_dir),
                                                settings=Settings(anonymized_telemetry=False))
        self.embedding_fn = DefaultEmbeddingFunction()  # ONNX all-MiniLM-L6-v2, runs locally
        self.collection = self.client.get_or_create_collection(
            COLLECTION, embedding_function=self.embedding_fn, metadata={"hnsw:space": "cosine"})
        self.stats: dict = {}

    def build(self, force: bool = False) -> dict:
        """Ingest -> chunk -> embed -> upsert. Idempotent: skips work when the corpus hash is unchanged."""
        digest = corpus_hash(self.directory)
        current = (self.collection.metadata or {}).get("corpus_hash")
        if current == digest and not force and self.collection.count() > 0:
            self.stats = {"status": "up-to-date", "chunks": self.collection.count(), "corpus_hash": digest}
            return self.stats
        docs = load_documents(self.directory)
        chunks = chunk_documents(docs)
        self.client.delete_collection(COLLECTION)
        self.collection = self.client.create_collection(
            COLLECTION, embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine", "corpus_hash": digest})
        self.collection.add(
            ids=[f"{c.metadata['source']}#{c.metadata['section']}#{c.metadata['chunk']}" for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[c.metadata for c in chunks],
        )
        self.stats = {"status": "built", "documents": len(docs), "chunks": len(chunks), "corpus_hash": digest}
        return self.stats

    # ---- 5. retrieval --------------------------------------------------------------
    def search(self, query: str, k: int = 4, component_id: str | None = None) -> list[Hit]:
        where = {f"cid:{component_id.strip()}": True} if component_id else None
        res = self.collection.query(query_texts=[query], n_results=k, where=where)
        hits = []
        for text, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0], strict=True):
            hits.append(Hit(text=text, score=round(1.0 - dist, 4), metadata=meta))
        return hits


_INDEX: DatasheetIndex | None = None
_INDEX_LOCK = threading.Lock()


def get_index() -> DatasheetIndex:
    """Process-wide index, built once on first use.

    Thread-safe: LangChain runs sync tools in worker threads, and the four parallel research
    agents would otherwise race to open the same Chroma directory.
    """
    global _INDEX
    with _INDEX_LOCK:
        if _INDEX is None:
            index = DatasheetIndex()
            index.build()
            _INDEX = index
        return _INDEX


# ---- 6. guaranteed evidence: one cited passage per shortlisted component ------------------


def evidence_for_component(component_id: str, query: str, k: int = 1,
                           index: DatasheetIndex | None = None) -> list[dict]:
    """Top datasheet passages tagged with `component_id`, as citation dicts (claim, source, page, url).

    Called by the research node for every shortlisted part, so each candidate carries datasheet
    evidence whether or not the LLM chose to call `search_datasheets`.
    """
    hits = (index or get_index()).search(query, k=k, component_id=component_id)
    out = []
    for h in hits:
        m = h.metadata
        passage = h.text.split("\n", 1)[-1].strip()  # drop the "title - section" prefix line
        out.append({"claim": f"[{m.get('section')}] {passage[:400]}", "source": m.get("source", ""),
                    "page": m.get("page") or "web", "url": m.get("source_url") or None,
                    "component_id": component_id})
    return out
