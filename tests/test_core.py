import pytest

from config import Config
from embedding_generator import EmbeddingGenerator
from offline import ScriptedModel, hash_embedding
from text_processor import TextProcessor
from vector_database import VectorDatabase


# ---- chunking -------------------------------------------------------------
def test_chunks_have_no_redundant_tail():
    tp = TextProcessor(1000, 200)
    for n in (1050, 1700, 2500, 5000):
        chunks = tp.create_chunks(" ".join(f"k{i}" for i in range(n // 5)))  # unique words
        for a, b in zip(chunks, chunks[1:]):
            assert b not in a, f"last chunk is a copy of the previous one for n={n}"


def test_chunks_cover_the_whole_text_and_respect_size():
    text = " ".join(f"w{i}" for i in range(3000))
    chunks = TextProcessor(500, 100).create_chunks(text)
    assert all(len(c) <= 500 for c in chunks)
    assert chunks[0].startswith("w0") and chunks[-1].endswith("w2999")


def test_chunks_make_progress_with_huge_overlap():
    assert len(TextProcessor(100, 99).create_chunks("a" * 1000)) < 1000  # terminates


def test_empty_text_gives_no_chunks():
    assert TextProcessor().create_chunks("   ") == []


# ---- offline embeddings ---------------------------------------------------
def test_hash_embedding_is_deterministic_and_normalised():
    a = hash_embedding("Tarım devrimi nedir")
    assert a == hash_embedding("Tarım devrimi nedir")
    assert abs(sum(x * x for x in a) - 1) < 1e-5


def test_related_texts_are_closer_than_unrelated():
    q = hash_embedding("yerleşik hayata geçiş")
    rel = hash_embedding("Yerleşik hayata geçişin sonuçları büyüktür")
    unrel = hash_embedding("uzay roketi fırlatma")
    dot = lambda x, y: sum(i * j for i, j in zip(x, y))
    assert dot(q, rel) > dot(q, unrel)


def test_embedding_generator_uses_offline_backend():
    assert Config.OFFLINE
    assert len(EmbeddingGenerator().generate_single_embedding("merhaba")) == 256


# ---- scripted model -------------------------------------------------------
@pytest.mark.parametrize("q,expected", [
    ("Merhaba", "NO_SEARCH"),
    ("Kitapta nelerden bahsediliyor?", "BOOK_ONLY"),
    ("Derste ne anlatıldı?", "TRANSCRIPT_ONLY"),
    ("Tarım devrimi nedir?", "BOTH_SOURCES"),
])
def test_scripted_decision(q, expected):
    assert ScriptedModel().generate_content(f"...KARAR VER: ...\nKULLANICI SORUSU: {q}\n\nKararını").text == expected


# ---- vector database ------------------------------------------------------
def test_vector_db_roundtrip():
    db = VectorDatabase()
    col = db.create_collection("t_roundtrip", {"content_hash": "x"})
    texts = ["Tarım ve hayvancılık", "Uzay araştırmaları", "Kalıcı evler ve depolama"]
    db.add_documents(col, texts, [hash_embedding(t) for t in texts])
    res = db.search_similar(col, hash_embedding("tarımsal üretim"), n_results=1)
    assert res["documents"][0][0] == texts[0]
    assert db.get_collection("t_roundtrip").metadata["content_hash"] == "x"
