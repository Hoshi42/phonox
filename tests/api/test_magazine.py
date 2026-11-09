"""Isolated magazine lifecycle, snapshot and PDF acceptance tests; no paid APIs."""

import json
import os
import time
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import backend.database as database
import backend.magazine_service as service
from backend.api.magazine import router
from backend.api.register import router as register_router
from backend.database import Base, CollectionMagazine, VinylImage, VinylRecord, get_db
from backend.magazine_models import MagazineDraft, MagazineSettings


class DeferredExecutor:
    def __init__(self):
        self.jobs = []

    def submit(self, function, *args):
        self.jobs.append((function, args))

    def drain(self):
        while self.jobs:
            function, args = self.jobs.pop(0)
            function(*args)


@pytest.fixture
def environment(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    executor = DeferredExecutor()
    monkeypatch.setattr(database, "SessionLocal", factory)
    monkeypatch.setattr(service, "MAGAZINE_ROOT", tmp_path / "magazines")
    monkeypatch.setattr("backend.api.magazine.EXECUTOR", executor)
    app = FastAPI()
    app.include_router(router)
    app.include_router(register_router)

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, db=factory, executor=executor, root=tmp_path)
    engine.dispose()


def add_record(env, artist="Artist One", title="First Album", user="alice", value=12.5, images=0):
    with env.db() as db:
        record = VinylRecord(artist=artist, title=title, user_tag=user, in_register=True,
                             year=1984, estimated_value_eur=value, condition="good",
                             user_notes="PRIVATE COLLECTOR NOTE", genres='["Jazz"]')
        db.add(record)
        db.flush()
        record_id = record.id
        for index in range(images):
            source = env.root / f"{record_id}-{index}.png"
            tint = record_id.replace("-", "")[index * 6:index * 6 + 6].ljust(6, "7")
            photo = Image.new("RGB", (1800, 2400), f"#{tint}")
            draw = ImageDraw.Draw(photo)
            draw.ellipse((180, 520, 1620, 1960), fill="#152125")
            draw.ellipse((700, 1040, 1100, 1440), fill="#eee3c4")
            photo.save(source)
            db.add(VinylImage(record_id=record_id, filename=f"view-{index}.png",
                              content_type="image/png", file_size=source.stat().st_size,
                              file_path=str(source), is_primary=index == 0))
        db.commit()
    return record_id


def status(env, user="alice"):
    response = env.client.get("/api/magazine", params={"user_tag": user})
    assert response.status_code == 200, response.text
    return response.json()


def prepare(env, user="alice", **settings):
    response = env.client.post("/api/magazine/prepare", params={"user_tag": user},
                               json={"research": False, **settings})
    assert response.status_code == 202, response.text
    env.executor.drain()
    result = status(env, user)
    assert result["status"] == "draft", result
    return result


def publish(env, user="alice"):
    current = status(env, user)
    response = env.client.post("/api/magazine/publish", params={"user_tag": user},
                               json={"version": current["draft_version"]})
    assert response.status_code == 202, response.text
    env.executor.drain()
    result = status(env, user)
    assert result["status"] == "complete", result
    return result


def reader(env, user="alice"):
    with env.db() as db:
        magazine = db.query(CollectionMagazine).filter_by(user_tag=user).one()
        return PdfReader(service.magazine_directory(magazine.id) / magazine.current_pdf)


def outline_entries(entries):
    for entry in entries:
        if isinstance(entry, list):
            yield from outline_entries(entry)
        else:
            yield entry


def test_empty_and_missing_user_are_rejected(environment):
    env = environment
    assert env.client.get("/api/magazine").status_code == 422
    assert env.client.get("/api/magazine?user_tag=%20").status_code == 400
    assert env.client.post("/api/magazine/prepare?user_tag=alice", json={"research": False}).status_code == 400
    assert status(env)["status"] == "not_created"


def test_research_requires_consent(environment):
    env = environment
    add_record(env)
    response = env.client.post("/api/magazine/prepare?user_tag=alice", json={"research": True})
    assert response.status_code == 400
    assert not env.executor.jobs


def test_one_magazine_per_user_and_duplicate_start(environment):
    env = environment
    add_record(env)
    add_record(env, user="bob", title="Bob's Album")
    for _ in range(2):
        assert env.client.post("/api/magazine/prepare?user_tag=alice", json={"research": False}).status_code == 202
    assert len(env.executor.jobs) == 1
    env.executor.drain()
    alice = status(env)
    bob = prepare(env, "bob")
    assert alice["id"] != bob["id"]
    assert [record["title"] for record in alice["draft"]["records"]] == ["First Album"]
    assert [record["title"] for record in bob["draft"]["records"]] == ["Bob's Album"]
    with env.db() as db:
        assert db.query(CollectionMagazine).count() == 2
    assert env.client.get("/api/magazine/pdf?user_tag=bob").status_code == 404


def page_text(document, index):
    return document.pages[index].extract_text()


def test_landscape_half_page_magazine_structure_images_fonts_links(environment):
    env = environment
    for artist in ("Artist One", "Artist Two", "Artist Three"):
        for index in range(2):
            add_record(env, artist=artist, title=f"{artist} Album {index}", images=2)
    draft = prepare(env, title="The Collection / Édition", subtitle="Records and stories")
    result = publish(env)
    document = reader(env)
    assert result["record_count"] == 6
    assert result["page_count"] == len(document.pages)
    assert all(float(page.mediabox.width) > float(page.mediabox.height) for page in document.pages)
    assert abs(float(document.pages[0].mediabox.width) - 841.89) < 0.5
    text = "\n".join(page.extract_text() for page in document.pages)
    for heading in ("Foreword", "Contents", "The collection at a glance", "Sources"):
        assert heading in text
    assert "PRIVATE COLLECTOR NOTE" not in text
    for absent in ("unknown", "not available", "not recorded", "Value unavailable", "No researched"):
        assert absent.lower() not in text.lower()
    entries = list(outline_entries(document.outline))
    for entry in entries:
        destination = document.get_destination_page_number(entry)
        assert 0 <= destination < len(document.pages)
        assert entry.title in document.pages[destination].extract_text()
    album_entries = [entry for entry in entries if " Album " in entry.title]
    assert len(album_entries) == 6
    # Every album owns one half page, so a page never carries more than two albums.
    per_page = Counter(document.get_destination_page_number(entry) for entry in album_entries)
    assert max(per_page.values()) == 2 and len(per_page) == 3
    assert sum(len(page.images) for page in document.pages) >= 12  # both views of all six albums
    for page in document.pages:
        for font in page["/Resources"].get("/Font", {}).values():
            descriptor = font.get_object().get("/FontDescriptor")
            if descriptor:
                assert "/FontFile2" in descriptor.get_object()
    assert len(env.client.get("/api/magazine/pdf?user_tag=alice").content) < 1_500_000
    response = env.client.get("/api/magazine/pdf?user_tag=alice")
    assert response.content.startswith(b"%PDF-")
    assert response.headers["content-disposition"].startswith("inline")
    assert env.client.get("/api/magazine/pdf?user_tag=alice&download=true").headers["content-disposition"].startswith("attachment")
    assert draft["draft"]["records"][0]["images"][0]["asset"] is None
    assert str(env.root) not in json.dumps(draft)


def test_snapshot_preserves_deleted_images_and_original_data(environment):
    env = environment
    record_id = add_record(env, images=1)
    prepared = prepare(env)
    photo_id = prepared["draft"]["records"][0]["images"][0]["id"]
    with env.db() as db:
        record = db.get(VinylRecord, record_id)
        Path(record.images[0].file_path).unlink()
        record.title = "Changed after snapshot"
        db.commit()
    assert env.client.get(f"/api/magazine/images/{photo_id}?user_tag=alice").status_code == 200
    assert env.client.get(f"/api/magazine/images/{photo_id}?user_tag=bob").status_code == 404
    publish(env)
    text = "\n".join(page.extract_text() for page in reader(env).pages)
    assert "First Album" in text and "Changed after snapshot" not in text
    assert status(env)["changes"]["changed"] == 1


def test_update_reuses_identity_and_rebuilds_chapters_counts_and_links(environment):
    env = environment
    add_record(env, images=1)
    first = prepare(env)
    publish(env)
    add_record(env, artist="A New Artist", title="A New Album")
    add_record(env, artist="Artist One", title="Second Album")
    assert status(env)["changes"]["added"] == 2
    updated = prepare(env)
    assert updated["id"] == first["id"]
    assert len(updated["draft"]["artists"]) == 2
    result = publish(env)
    assert result["edition"] == 2 and result["record_count"] == 3
    assert result["changes"] == {"added": 0, "changed": 0, "removed": 0}
    assert len(list(service.magazine_directory(result["id"]).glob("*.pdf"))) == 1
    assert [record["title"] for record in updated["draft"]["records"]][:1] == ["A New Album"]


def test_same_count_detects_additions_removals_and_image_changes(environment):
    env = environment
    record_id = add_record(env, images=1)
    prepare(env)
    publish(env)
    with env.db() as db:
        db.delete(db.get(VinylRecord, record_id))
        db.commit()
    add_record(env, title="Replacement")
    assert status(env)["changes"] == {"added": 1, "removed": 1, "changed": 0}


def test_edited_texts_and_groupings_survive_update(environment):
    env = environment
    record_id = add_record(env)
    prepared = prepare(env)
    draft = prepared["draft"]
    response = env.client.put("/api/magazine/draft?user_tag=alice", json={
        "version": prepared["draft_version"], "preface": "My own foreword.",
        "records": [{"id": record_id, "group": "My Artist Group", "description": "My own description."}],
        "artists": [{"name": draft["artists"][0]["name"], "portrait": "My own artist portrait."}],
    })
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["draft"]["artists"][0]["name"] == "My Artist Group"
    assert updated["draft"]["artists"][0]["portrait"] == "My own artist portrait."
    stale = env.client.post("/api/magazine/publish?user_tag=alice",
                            json={"version": prepared["draft_version"]})
    assert stale.status_code == 409
    publish(env)
    with env.db() as db:
        record = db.get(VinylRecord, record_id)
        record.year = 1999
        db.commit()
    draft = prepare(env, preface="My own foreword.")["draft"]
    assert draft["settings"]["preface"] == "My own foreword."
    assert draft["records"][0]["description"] == "My own description."
    assert draft["records"][0]["group"] == "My Artist Group"
    assert draft["artists"][0]["portrait"] == "My own artist portrait."
    assert any("Review edited description" in warning for warning in draft["warnings"])
    add_record(env, title="New album for the same artist")
    next_draft = prepare(env)["draft"]
    assert len(next_draft["artists"]) == 1
    assert all(record["group"] == "My Artist Group" for record in next_draft["records"])


def test_unknown_values_duplicates_compilations_and_artist_normalization(environment):
    env = environment
    add_record(env, artist="  Artist One ", title="Same Album", value=None)
    add_record(env, artist="artist one", title="Same Album", value=0)
    add_record(env, artist=None, title=None, value=None)
    add_record(env, artist="Various Artists", title="Compilation", value=None)
    prepared = prepare(env)
    assert len(prepared["draft"]["artists"]) == 3
    publish(env)
    text = "\n".join(page.extract_text() for page in reader(env).pages)
    assert "EUR 0" in text and "across 1 of 4 records" in text
    assert "Unavailable" not in text and "unknown" not in text.lower()
    assert "Copy 1" in text and "Copy 2" in text
    assert "Other records" in text and "Unknown Artist" not in text


def test_failed_update_and_cancellation_keep_previous_pdf(environment, monkeypatch):
    env = environment
    add_record(env)
    prepare(env)
    first = publish(env)
    old = env.client.get("/api/magazine/pdf?user_tag=alice").content
    prepare(env)

    def failure(*args):
        raise RuntimeError("Test typesetting failure")

    monkeypatch.setattr("backend.magazine_pdf.render_magazine", failure)
    env.client.post("/api/magazine/publish?user_tag=alice", json={"version": status(env)["draft_version"]})
    env.executor.drain()
    assert status(env)["status"] == "failed"
    assert env.client.get("/api/magazine/pdf?user_tag=alice").content == old
    assert status(env)["edition"] == first["edition"]
    env.client.post("/api/magazine/prepare?user_tag=alice", json={"research": False})
    env.client.post("/api/magazine/cancel?user_tag=alice")
    env.executor.drain()
    assert status(env)["status"] == "cancelled"
    assert env.client.get("/api/magazine/pdf?user_tag=alice").content == old


def test_cleanup_failure_does_not_remove_successfully_published_pdf(environment, monkeypatch):
    env = environment
    add_record(env)
    prepare(env)
    publish(env)
    prepare(env)

    def failure(*args, **kwargs):
        raise OSError("Simulated cleanup failure")

    monkeypatch.setattr(service, "cleanup_assets", failure)
    result = publish(env)
    assert result["edition"] == 2
    assert env.client.get("/api/magazine/pdf?user_tag=alice").content.startswith(b"%PDF-")


def test_recovery_preserves_current_pdf_and_never_restarts_paid_work(environment):
    env = environment
    add_record(env)
    prepare(env)
    publish(env)
    env.client.post("/api/magazine/prepare?user_tag=alice", json={"research": False})
    env.executor.jobs.clear()
    with env.db() as db:
        service.maintain_magazines(db, recover=True)
    assert status(env)["status"] == "failed"
    assert status(env)["has_pdf"]
    assert not env.executor.jobs
    with env.db() as db:
        service.maintain_magazines(db)
    assert env.client.get("/api/magazine/pdf?user_tag=alice").status_code == 200


def test_delete_removes_magazine_not_collection(environment):
    env = environment
    add_record(env)
    prepared = prepare(env)
    publish(env)
    response = env.client.delete("/api/magazine?user_tag=alice")
    assert response.status_code == 204
    assert not service.magazine_directory(prepared["id"]).exists()
    assert status(env)["status"] == "not_created"
    with env.db() as db:
        assert db.query(VinylRecord).count() == 1


def test_missing_and_corrupt_images_are_reported_without_false_changes(environment):
    env = environment
    record_id = add_record(env, images=2)
    with env.db() as db:
        record = db.get(VinylRecord, record_id)
        Path(record.images[0].file_path).unlink()
        Path(record.images[1].file_path).write_bytes(b"not an image")
    prepared = prepare(env)
    assert sum("Image unavailable" in warning for warning in prepared["draft"]["warnings"]) == 2
    publish(env)
    assert status(env)["changes"]["changed"] == 0


def test_budget_is_hard_and_all_providers_are_bounded(environment, monkeypatch):
    env = environment
    for index in range(8):
        add_record(env, artist=f"Artist {index}", title=f"Album {index}")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-a-real-key")
    calls = []

    def lookup(artist, title, fallback_on_error):
        calls.append("database")
        return {"artist": artist, "title": title}

    def research(query, instruction, budget, candidates=None):
        budget.reserve()
        calls.append("search")
        budget.reserve()
        calls.append("ai")
        source = service.MagazineSource(title="Source", url="https://example.org/music", accessed_at=service.utc_now())
        text = "Original researched editorial text. " * (40 if "portrait" in instruction else 25)
        return service.ResearchAnswer(text=text, used_sources=[0],
                                      value_eur=None), [source]

    monkeypatch.setenv("MUSICBRAINZ_ENABLED", "true")
    monkeypatch.setattr("backend.agent.metadata.lookup_discogs_metadata", lookup)
    monkeypatch.setattr("backend.agent.metadata.lookup_musicbrainz_metadata", lookup)
    monkeypatch.setattr(service, "research_text", research)
    prepared = prepare(env, research=True, consent=True)
    assert prepared["draft"]["steps_used"] == 20
    assert len(calls) == 20
    assert calls.count("database") == 2
    assert any("budget" in warning.lower() for warning in prepared["draft"]["warnings"])
    assert "PRIVATE COLLECTOR NOTE" not in json.dumps(prepared["draft"])


def test_researched_values_keep_actual_dates_on_update(environment, monkeypatch):
    env = environment
    add_record(env)
    prepared = prepare(env)
    with env.db() as db:
        magazine = db.query(CollectionMagazine).one()
        draft = MagazineDraft.model_validate_json(magazine.draft_payload)
        draft.records[0].value_eur = 25
        draft.records[0].value_kind = "researched"
        draft.records[0].valued_at = "2020-01-01T00:00:00+00:00"
        magazine.draft_payload = draft.model_dump_json()
        db.commit()
    publish(env)
    updated = prepare(env, refresh_values=False)
    assert updated["id"] == prepared["id"]
    assert updated["draft"]["records"][0]["value_eur"] == 25
    assert updated["draft"]["records"][0]["valued_at"].startswith("2020-01-01")


def test_long_titles_and_hundred_record_collection(environment):
    env = environment
    templates = []
    for index in range(100):
        record_id = add_record(env, artist=f"Artist {index % 3}",
                               title=f"{index:03d} / " + "Édition vinyl " * 10,
                               images=5 if index == 0 else 0)
        with env.db() as db:
            if index == 0:
                templates = [(image.filename, image.content_type, image.file_size, image.file_path)
                             for image in db.get(VinylRecord, record_id).images]
            else:
                for image_index, (name, content_type, size, path) in enumerate(templates):
                    db.add(VinylImage(record_id=record_id, filename=name, content_type=content_type,
                                     file_size=size, file_path=path, is_primary=image_index == 0))
                db.commit()
    prepare(env, title="A long magazine title " * 8)
    result = publish(env)
    assert result["record_count"] == 100
    # Identical test images are stored once per page, so count unique images per half-page pair.
    assert sum(len(page.images) for page in reader(env).pages) >= 250
    assert result["page_count"] < 80  # two albums per landscape page
    assert len([entry for entry in outline_entries(reader(env).outline) if "Édition vinyl" in entry.title]) == 100


def test_automatic_foreword_is_updated_but_user_text_is_preserved(environment):
    env = environment
    add_record(env)
    first = prepare(env, title="My custom magazine")
    assert "1 record by 1 artist or group." in first["draft"]["settings"]["preface"]
    publish(env)
    add_record(env, title="Second Album")
    updated = prepare(env)
    assert "2 records" in updated["draft"]["settings"]["preface"]
    assert updated["draft"]["settings"]["title"] == "My custom magazine"


def test_hard_ai_limits_source_validation_and_no_invented_prices(environment, monkeypatch):
    env = environment
    add_record(env)
    with env.db() as db:
        magazine = CollectionMagazine(user_tag="alice")
        db.add(magazine)
        db.flush()
        draft = service.prepare_draft(db, magazine, MagazineSettings(research=False))
    calls = []

    class Client:
        def __init__(self, **kwargs):
            assert kwargs["max_retries"] == 0
            self.messages = self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text=json.dumps({
                    "text": "An original text based on the supplied sources.",
                    "used_sources": [0], "value_eur": 500, "valuation_basis": "album_level",
                }))], stop_reason="end_turn")

    monkeypatch.setattr(service, "Anthropic", Client)
    monkeypatch.setattr("backend.tools.web_tools.WebSearchTool.search", lambda *args, **kwargs: [{
        "title": "Music history", "url": "https://example.org/history", "content": "Release history. " * 4000,
    }])
    budget = service.ResearchBudget(draft, lambda: None)
    answer, sources = service.research_text("Artist Album", "Describe the record.", budget)
    assert draft.steps_used == 2
    assert calls[0]["max_tokens"] == 1200
    assert len(calls[0]["messages"][0]["content"].encode()) <= service.INPUT_BYTE_LIMIT
    assert answer.value_eur is None and answer.valuation_basis == "insufficient"
    assert sources[0].url == "https://example.org/history"
    assert "PRIVATE COLLECTOR NOTE" not in json.dumps(calls)
    draft.steps_used = 20
    with pytest.raises(ValueError, match="limit"):
        budget.reserve()
    assert draft.steps_used == 20


def test_image_modification_is_detected_and_export_does_not_write_collection(environment):
    env = environment
    record_id = add_record(env, images=1)
    with env.db() as db:
        before = db.get(VinylRecord, record_id).to_dict()
    prepare(env)
    publish(env)
    with env.db() as db:
        row = db.get(VinylRecord, record_id)
        assert row.to_dict() == before
        path = Path(row.images[0].file_path)
        Image.new("RGB", (1800, 2400), "blue").save(path)
    assert status(env)["changes"]["changed"] == 1


def test_unused_work_is_cleaned_but_current_assets_are_kept(environment):
    env = environment
    add_record(env, images=1)
    created = prepare(env)
    publish(env)
    directory = service.magazine_directory(created["id"])
    orphan = directory / "assets" / ("0" * 64 + ".jpg")
    orphan.write_bytes(b"unused")
    old_pdf = directory / "unused.pdf"
    old_pdf.write_bytes(b"unused")
    old = time.time() - 86400
    os.utime(orphan, (old, old))
    os.utime(old_pdf, (old, old))
    with env.db() as db:
        magazine = db.query(CollectionMagazine).one()
        payload = service.load_payload(magazine.current_payload)
        asset = service.asset_path(magazine.id, payload.records[0].images[0].asset)
        os.utime(asset, (old, old))
        service.maintain_magazines(db)
    assert not orphan.exists() and not old_pdf.exists()
    assert asset.exists()
    assert env.client.get("/api/magazine/pdf?user_tag=alice").status_code == 200


def test_database_uniqueness_is_not_only_a_ui_rule(environment):
    from sqlalchemy.exc import IntegrityError
    env = environment
    with env.db() as db:
        db.add(CollectionMagazine(user_tag="alice"))
        db.commit()
        db.add(CollectionMagazine(user_tag="alice"))
        with pytest.raises(IntegrityError):
            db.commit()


def test_unavailable_worker_is_reported_and_retryable(environment, monkeypatch):
    env = environment
    add_record(env)

    def unavailable(*args):
        raise RuntimeError("Worker is shutting down")

    monkeypatch.setattr(env.executor, "submit", unavailable)
    response = env.client.post("/api/magazine/prepare?user_tag=alice", json={"research": False})
    assert response.status_code == 503
    assert status(env)["status"] == "failed"


def test_user_with_empty_collection_and_saved_magazine_remains_selectable(environment):
    env = environment
    record_id = add_record(env)
    prepare(env)
    publish(env)
    with env.db() as db:
        db.delete(db.get(VinylRecord, record_id))
        db.commit()
    response = env.client.get("/api/register/users")
    assert response.status_code == 200
    assert "alice" in response.json()
    assert status(env)["changes"]["removed"] == 1
    assert env.client.get("/api/magazine/pdf?user_tag=alice").status_code == 200


def test_portrait_half_page_and_downscaled_images(environment):
    env = environment
    record_id = add_record(env, images=1)
    with env.db() as db:
        image = db.get(VinylRecord, record_id).images[0]
        Image.new("RGB", (3840, 5400), "#315966").save(image.file_path)
    prepared = prepare(env)
    draft = prepared["draft"]
    portrait = "This sample portrait describes only the fictional test collection and its records. " * 15
    response = env.client.put("/api/magazine/draft?user_tag=alice", json={
        "version": prepared["draft_version"], "preface": draft["settings"]["preface"],
        "records": [{"id": record_id, "group": "Artist One",
                     "description": draft["records"][0]["description"]}],
        "artists": [{"name": "Artist One", "portrait": portrait}],
    })
    assert response.status_code == 200, response.text
    publish(env)
    document = reader(env)
    texts = [page.extract_text() for page in document.pages]
    cell_page = next(text for text in texts if "ARTIST ONE" in text)
    assert "This sample portrait" in cell_page and "First Album" in cell_page  # portrait and album share the page
    # The 3840x5400 source is resampled to what a half-page cell needs, far below the original size.
    widths = [image.image.width for page in document.pages for image in page.images]
    assert widths and max(widths) <= 1800 and min(widths) < 700
    assert len(env.client.get("/api/magazine/pdf?user_tag=alice").content) < 600_000


def test_old_placeholder_texts_never_reach_the_pdf(environment):
    env = environment
    add_record(env, images=1)
    prepare(env)
    with env.db() as db:
        magazine = db.query(CollectionMagazine).one()
        payload = MagazineDraft.model_validate_json(magazine.draft_payload)
        payload.records[0].description = "x. A researched musical description is not available yet. y."
        payload.artists[0].portrait = "A researched artist portrait is not available yet."
        magazine.draft_payload = payload.model_dump_json()
        db.commit()
    publish(env)
    text = "\n".join(page.extract_text() for page in reader(env).pages)
    assert "not available yet" not in text and "ARTIST\n" not in text


def test_overlong_text_is_shortened_to_stay_on_its_half_page(environment):
    env = environment
    record_id = add_record(env, images=1)
    prepared = prepare(env)
    draft = prepared["draft"]
    long_text = "A very long editorial sentence about this particular record. " * 120
    env.client.put("/api/magazine/draft?user_tag=alice", json={
        "version": prepared["draft_version"], "preface": draft["settings"]["preface"],
        "records": [{"id": record_id, "group": "Artist One", "description": long_text}],
        "artists": [{"name": "Artist One", "portrait": ""}],
    })
    result = publish(env)
    document = reader(env)
    assert result["page_count"] == len(document.pages)
    assert any("Text shortened to fit one half page" in note for note in status(env)["warnings"])
    cell_pages = [page for page in document.pages if "First Album" in page.extract_text() and "…" in page.extract_text()]
    assert len(cell_pages) == 1


def test_job_progress_math_is_bounded_and_monotonic_per_stage():
    job = service.JobProgress("x", done=5, total=10, base=35.0, span=65.0)
    assert job.percent() == 67.5
    assert service.JobProgress("x").percent() is None  # nothing measurable yet
    assert service.JobProgress("x", done=50, total=10, base=35.0, span=65.0).percent() == 99.0


def test_status_reports_progress_only_while_a_job_runs(environment):
    env = environment
    add_record(env)
    env.client.post("/api/magazine/prepare?user_tag=alice", json={"research": False})
    queued = status(env)
    assert queued["status"] == "preparing"
    assert queued["progress"]["label"] == "Waiting to start" and queued["progress"]["percent"] is None
    env.executor.drain()
    finished = status(env)
    assert finished["status"] == "draft" and finished["progress"] is None
    assert finished["id"] not in service.PROGRESS


def test_preparation_and_typesetting_report_measurable_progress(environment, monkeypatch):
    env = environment
    for index in range(5):
        add_record(env, title=f"Album {index}", images=1)
    seen = []
    original = service.set_progress

    def record(magazine_id, label, done=0, total=0, base=0.0, span=100.0):
        seen.append((label, done, total, base, span))
        original(magazine_id, label, done, total, base, span)

    monkeypatch.setattr(service, "set_progress", record)
    prepare(env)
    freezing = [item for item in seen if item[0] == "Freezing collection data and images" and item[2]]
    assert [item[1] for item in freezing] == sorted(item[1] for item in freezing)
    assert freezing[-1][1:3] == (5, 5)
    assert freezing[-1][4] == 100.0  # without research the snapshot is the whole job

    seen.clear()
    publish(env)
    typesetting = [item for item in seen if item[0].startswith("Typesetting") and item[2]]
    assert typesetting and all(done <= total for _, done, total, *_ in typesetting)
    assert typesetting[-1][1] > typesetting[0][1]


def test_research_share_of_the_progress_is_reserved_when_enabled(environment, monkeypatch):
    env = environment
    add_record(env)
    seen = []
    original = service.set_progress
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-a-real-key")
    monkeypatch.setattr("backend.agent.metadata.lookup_discogs_metadata", lambda *a, **k: None)
    monkeypatch.setattr("backend.agent.metadata.lookup_musicbrainz_metadata", lambda *a, **k: None)
    monkeypatch.setattr(service, "research_text", lambda *a, **k: (_ for _ in ()).throw(ValueError("offline")))
    monkeypatch.setattr(service, "set_progress", lambda mid, *args: (seen.append(args), original(mid, *args)))
    prepare(env, research=True, consent=True)
    assert any(args[0].startswith("Freezing") and args[4] == 35.0 for args in seen)
    assert any(args[0].startswith("Researching") and args[2] == service.STEP_LIMIT and args[3] == 35.0
               for args in seen)


def test_lost_commit_acknowledgement_does_not_delete_the_published_pdf(environment, monkeypatch):
    env = environment
    add_record(env)
    prepare(env)
    publish(env)
    prepare(env)

    class AmbiguousSession(Session):
        def commit(self):
            publishing = any(isinstance(row, CollectionMagazine) and row.status == "complete"
                             for row in self.dirty)
            super().commit()
            if publishing:
                raise OSError("Simulated lost database commit acknowledgement")

    monkeypatch.setattr(database, "SessionLocal",
                        sessionmaker(bind=env.db.kw["bind"], class_=AmbiguousSession))
    result = publish(env)
    assert result["edition"] == 2
    assert env.client.get("/api/magazine/pdf?user_tag=alice").content.startswith(b"%PDF-")
