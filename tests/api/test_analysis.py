"""The latest collection analysis is stored per user and can always be reopened."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.analysis import router
from backend.database import Base, CollectionAnalysis, get_db


@pytest.fixture
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    app = FastAPI()
    app.include_router(router)

    def override():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client, factory
    engine.dispose()


def body(summary="## Strengths\nA fine jazz collection.", count=3, value=120.5):
    return {"summary": summary, "record_count": count, "total_value_eur": value}


def test_nothing_stored_yet_is_a_clean_404(env):
    client, _ = env
    assert client.get("/api/analysis", params={"user_tag": "alice"}).status_code == 404


def test_saved_analysis_can_be_reopened_and_is_replaced_by_the_next(env):
    client, factory = env
    saved = client.put("/api/analysis?user_tag=alice", json=body())
    assert saved.status_code == 200
    reopened = client.get("/api/analysis?user_tag=alice").json()
    assert reopened["summary"].startswith("## Strengths") and reopened["record_count"] == 3
    assert reopened["total_value_eur"] == 120.5 and reopened["created_at"]

    client.put("/api/analysis?user_tag=alice", json=body("Second analysis", 5, None))
    latest = client.get("/api/analysis?user_tag=alice").json()
    assert latest["summary"] == "Second analysis" and latest["total_value_eur"] is None
    with factory() as db:
        assert db.query(CollectionAnalysis).count() == 1


def test_users_never_see_each_others_analysis(env):
    client, _ = env
    client.put("/api/analysis?user_tag=alice", json=body("Alice only"))
    assert client.get("/api/analysis?user_tag=bob").status_code == 404
    client.put("/api/analysis?user_tag=bob", json=body("Bob only"))
    assert client.get("/api/analysis?user_tag=alice").json()["summary"] == "Alice only"
    assert client.get("/api/analysis?user_tag=bob").json()["summary"] == "Bob only"


@pytest.mark.parametrize("payload", [
    {"summary": "", "record_count": 1},
    {"summary": "   ", "record_count": 1},
    {"summary": "x", "record_count": -1},
    {"summary": "x", "record_count": 1, "total_value_eur": -5},
    {"summary": "x" * 100_001, "record_count": 1},
    {"summary": "x", "record_count": 1, "unexpected": True},
])
def test_invalid_analyses_are_rejected_without_overwriting(env, payload):
    client, _ = env
    client.put("/api/analysis?user_tag=alice", json=body("Keep me"))
    assert client.put("/api/analysis?user_tag=alice", json=payload).status_code == 422
    assert client.get("/api/analysis?user_tag=alice").json()["summary"] == "Keep me"


def test_a_user_scope_is_required(env):
    client, _ = env
    assert client.get("/api/analysis").status_code == 422
    assert client.get("/api/analysis?user_tag=%20").status_code == 400
    assert client.put("/api/analysis?user_tag=%20", json=body()).status_code == 400
    assert client.put("/api/analysis?user_tag=" + "x" * 51, json=body()).status_code == 422
