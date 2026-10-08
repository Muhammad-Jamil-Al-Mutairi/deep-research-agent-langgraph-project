"""RAG pipeline: ingestion, chunking metadata, embeddings + Chroma, filtered retrieval."""

import pytest

from hermes.tools.research.rag import DatasheetIndex, chunk_documents, load_documents


def test_documents_load_with_front_matter():
    docs = load_documents()
    assert len(docs) >= 8
    for d in docs:
        assert d.metadata["source"].endswith(".md")
        assert d.metadata.get("source_url")
        assert d.metadata.get("component_ids")


def test_chunks_keep_citation_metadata():
    chunks = chunk_documents(load_documents())
    assert len(chunks) > 30
    esp = [c for c in chunks if "RF current" in c.metadata["section"]]
    assert esp and esp[0].metadata["page"] == "52"  # PDF page survives chunking
    assert esp[0].metadata["component_ids"] == "ADA-5400"
    lipo = [c for c in chunks if c.metadata["section"].startswith("Ovonic 3S 6000")][0]
    assert lipo.metadata["source_url"].startswith("https://us.ovonicshop.com/products/")  # section-level URL
    assert lipo.metadata["cid:OVO-3S-6000-80C"] is True


@pytest.mark.rag
def test_index_build_and_retrieval(tmp_path):
    index = DatasheetIndex(persist_dir=tmp_path / "chroma")
    stats = index.build()
    assert stats["status"] == "built" and stats["chunks"] > 30
    assert index.build()["status"] == "up-to-date"  # idempotent

    hits = index.search("recommended continuous load limit 37D gearmotor", k=3)
    assert hits[0].metadata["source"] == "pololu_37d_metal_gearmotors.md"
    assert "10 kg-cm" in hits[0].text

    hits = index.search("current draw when transmitting wifi", k=2)
    assert hits[0].metadata["page"] == "52"

    filtered = index.search("weight and size", k=2, component_id="OVO-3S-6000-80C")
    assert all("OVO-3S-6000-80C" in h.metadata["component_ids"] for h in filtered)


@pytest.mark.rag
def test_concurrent_first_use_from_worker_threads():
    """Parallel research agents call search_datasheets from worker threads at the same time."""
    from concurrent.futures import ThreadPoolExecutor

    from hermes.tools.research.tools import search_datasheets

    with ThreadPoolExecutor(max_workers=4) as pool:
        outs = list(pool.map(lambda q: search_datasheets.invoke({"query": q, "k": 1}),
                             ["motor torque limit", "battery weight", "driver current", "wheel bore"]))
    assert all("source:" in o and "unavailable" not in o for o in outs)


@pytest.mark.rag
def test_evidence_is_harvested_from_tool_output_not_llm_text():
    from langchain_core.messages import ToolMessage

    from hermes.agents.common import harvest_datasheet_evidence
    from hermes.tools.research.tools import search_datasheets

    out = search_datasheets.invoke({"query": "current draw when transmitting wifi", "k": 2})
    msgs = [ToolMessage(content=out, tool_call_id="1", name="search_datasheets"),
            ToolMessage(content="[1] source: fake.md | section: x | page: 1 | url: u | relevance: 0.9\nignored",
                        tool_call_id="2", name="search_components")]  # other tools are ignored
    ev = harvest_datasheet_evidence(msgs)
    assert len(ev) == 2 and all(e["source"].endswith(".md") and e["source"] != "fake.md" for e in ev)
    esp = [e for e in ev if e["page"] == "52"]
    assert esp and esp[0]["url"].startswith("https://documentation.espressif.com") and "240 mA" in esp[0]["claim"]


@pytest.mark.rag
def test_evidence_for_component_is_filtered_and_cited(tmp_path):
    from hermes.tools.research.rag import evidence_for_component

    index = DatasheetIndex(persist_dir=tmp_path / "chroma")
    index.build()
    ev = evidence_for_component("POL-4752", "Pololu 37D gearmotor ratings and limits", k=2, index=index)
    assert ev and all(e["component_id"] == "POL-4752" for e in ev)
    assert all(e["source"] == "pololu_37d_metal_gearmotors.md" and e["url"].startswith("https://") for e in ev)
    assert all(e["claim"].startswith("[") for e in ev)  # "[section] passage"
