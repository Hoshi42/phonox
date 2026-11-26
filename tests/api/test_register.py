import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.register import router
from backend.database import Base, VinylRecord, get_db


@pytest.fixture
def register_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    app = FastAPI()
    app.include_router(router)

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client, factory
    engine.dispose()


def test_update_register_accepts_combined_catalog_numbers(register_client):
    client, factory = register_client
    with factory() as db:
        record = VinylRecord(
            artist="7 Seconds",
            title="New Wind",
            user_tag="Jan",
            in_register=True,
        )
        db.add(record)
        db.commit()
        record_id = record.id

    catalog_number = "BYO LP07252/05 / EFA LP07252 08 / BYO 014 / LP07252"
    response = client.put(
        "/api/register/update",
        json={"record_id": record_id, "catalog_number": catalog_number},
    )

    assert response.status_code == 200, response.text
    assert response.json()["catalog_number"] == catalog_number


def test_favorite_flag_toggles_and_survives_other_updates(register_client):
    client, factory = register_client
    with factory() as db:
        record = VinylRecord(artist="Can", title="Tago Mago", user_tag="Jan", in_register=True)
        record.set_genres(["Krautrock"])
        db.add(record)
        db.commit()
        record_id = record.id

    listed = client.get("/api/register/", params={"user_tag": "Jan"}).json()
    assert listed[0]["is_favorite"] is False

    response = client.put("/api/register/update", json={"record_id": record_id, "is_favorite": True})
    assert response.status_code == 200, response.text
    assert response.json()["is_favorite"] is True

    # Updates that don't mention the flag must leave it untouched
    response = client.put("/api/register/update", json={"record_id": record_id, "condition": "good"})
    assert response.json()["is_favorite"] is True
    assert response.json()["genres"] == ["Krautrock"]

    response = client.put("/api/register/update", json={"record_id": record_id, "is_favorite": False})
    assert response.json()["is_favorite"] is False
