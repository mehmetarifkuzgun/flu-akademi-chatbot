import pytest

import main as main_module
from config import Config
from main import AgenticDemoChatbot


@pytest.fixture(scope="module")
def bot():
    b = AgenticDemoChatbot()
    b.setup_database()
    return b


def ask(bot, q):
    return "".join(bot.ask_question_agentic_stream(q))


def test_both_collections_are_loaded(bot):
    assert bot.transcript_collection.count() > 0 and bot.book_collection.count() > 0


def test_answer_is_built_from_retrieved_text_and_labelled(bot):
    answer = ask(bot, "Yerleşik hayata geçişin sonuçları nelerdir?")
    assert "Çevrimdışı demo" in answer          # never passes for model output
    assert "mülkiyet" in answer.lower() or "depol" in answer.lower()


def test_tool_choice_routes_to_the_right_source(bot):
    assert "Kitap" in ask(bot, "Kitapta nüfus baskısı kuramı nedir?") or "Kitap" in ask(bot, "kitap kuram")
    assert "Ders" in ask(bot, "Derste Göbekli Tepe'den bahsedildi mi?")


def test_greeting_does_not_search(bot):
    assert "ders kaynağı yok" in ask(bot, "Merhaba")


def test_unchanged_files_are_not_re_embedded(monkeypatch):
    b = AgenticDemoChatbot()
    b.setup_database()  # first call may build the collections

    def boom(*a, **k):
        raise AssertionError("embeddings regenerated although the content did not change")

    monkeypatch.setattr(b.embedding_generator, "generate_embeddings", boom)
    b.setup_database()
    assert b.book_collection.count() > 0


def test_changed_file_is_re_embedded(tmp_path, monkeypatch):
    f = tmp_path / "x.txt"
    f.write_text("Birinci metin. " * 50, encoding="utf-8")
    monkeypatch.setattr(Config, "BOOK_FILE", str(f))
    b = AgenticDemoChatbot()
    b._process_and_store_file(str(f), "t_changed")
    first = b.vector_db.get_collection("t_changed").metadata["content_hash"]
    f.write_text("İkinci, tamamen farklı bir metin. " * 50, encoding="utf-8")
    b._process_and_store_file(str(f), "t_changed")
    assert b.vector_db.get_collection("t_changed").metadata["content_hash"] != first
