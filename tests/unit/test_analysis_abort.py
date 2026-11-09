"""A failed image analysis aborts the identification instead of searching for an ERROR record."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.main  # noqa: F401  (routes registers itself on the app; import order avoids a cycle)
import backend.api.routes as routes
from backend.agent.graph import build_agent_graph, vision_failed
from backend.database import Base, VinylRecord, get_db


def failed_images_state():
    return {
        "images": [{"path": "a.jpg", "content": "aGVsbG8=", "content_type": "image/jpeg"}],
        "validation_passed": True,
        "evidence_chain": [],
        "confidence": 0.0,
    }


def test_vision_failed_detects_error_placeholder_and_error_key():
    assert vision_failed({"artist": "ERROR", "title": "ERROR"})
    assert vision_failed({"artist": "Danzig", "title": "ERROR"})
    assert vision_failed({"artist": "Unknown", "title": "Unknown", "error": "boom"})
    assert not vision_failed({"artist": "Danzig", "title": "Danzig"})
    assert not vision_failed({})
    assert not vision_failed(None)


def test_graph_stops_after_failed_vision_without_any_lookup():
    graph = build_agent_graph()

    with patch("backend.agent.graph.extract_vinyl_metadata_with_retry", side_effect=Exception("API down")), \
         patch("backend.agent.graph.lookup_metadata_from_both") as lookup, \
         patch("backend.agent.graph.search_spotify_album") as spotify, \
         patch("backend.agent.graph.search_vinyl_metadata") as websearch, \
         patch("backend.agent.graph.MetadataEnhancer") as enhancer:
        result = graph.invoke(failed_images_state(), config={"configurable": {"thread_id": "t"}})

    assert "API down" in result["error"]
    assert result["vision_extraction"]["artist"] == "ERROR"
    for step in (lookup, spotify, websearch, enhancer):
        step.assert_not_called()
    assert "confidence_gate" not in str(result.get("evidence_chain", ""))  # no later evidence was added
    assert not result.get("auto_commit")


def test_unvalidated_images_abort_with_the_validation_reason():
    graph = build_agent_graph()
    state = failed_images_state()
    state["images"] = []

    with patch("backend.agent.graph.lookup_metadata_from_both") as lookup:
        result = graph.invoke(state, config={"configurable": {"thread_id": "t"}})

    assert "No images provided" in result["error"]
    lookup.assert_not_called()


@pytest.fixture
def api(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    app = FastAPI()
    app.include_router(routes.router)

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, db=factory)
    engine.dispose()


def test_identify_marks_record_failed_and_skips_valuation(api, monkeypatch):
    class AbortedGraph:
        def invoke(self, state, config=None):
            return {
                "error": "Image analysis failed: API down",
                "validation_passed": True,
                "vision_extraction": {"artist": "ERROR", "title": "ERROR", "label": "ERROR", "genres": [],
                                      "confidence": 0.0, "error": "Image analysis failed: API down"},
                "evidence_chain": [],
            }

    search, claude = MagicMock(), MagicMock()
    monkeypatch.setattr(routes, "build_agent_graph", lambda: AbortedGraph())
    monkeypatch.setattr(routes.chat_tools, "search_and_scrape", search)
    monkeypatch.setattr(routes, "anthropic_client", claude)

    response = api.client.post("/api/v1/identify", files=[("files", ("a.jpg", b"x", "image/jpeg"))])

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "failed"
    assert body["error"] == "Image analysis failed: API down"
    assert "ERROR" not in str(body.get("metadata"))
    search.assert_not_called()
    claude.messages.create.assert_not_called()

    with api.db() as db:
        record = db.query(VinylRecord).one()
        assert record.status == "failed"
        assert record.artist is None and record.title is None
