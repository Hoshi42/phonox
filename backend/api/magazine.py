"""User-scoped collection magazine lifecycle and persistent PDF access."""

import logging
import uuid
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import CollectionMagazine, get_db
from backend.magazine_models import (
    MagazineApproval, MagazineArtist, MagazineDraftEdit, MagazineSettings, MagazineStatus,
)
from backend.magazine_service import (
    BUSY, EXECUTOR, asset_path, clear_progress, collection_records, delete_magazine_files, set_progress,
    get_status, load_payload, magazine_directory, record_order, run_preparation, run_render,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/magazine", tags=["magazine"])


def user_scope(user_tag: str = Query(min_length=1, max_length=50)) -> str:
    if not user_tag.strip():
        logger.warning("Magazine request rejected: empty user scope")
        raise HTTPException(400, "A collection user must be selected.")
    return user_tag


def find_magazine(db: Session, user_tag: str) -> CollectionMagazine:
    magazine = db.query(CollectionMagazine).filter_by(user_tag=user_tag).with_for_update().first()
    if magazine is None:
        raise HTTPException(404, "No magazine exists for this user.")
    return magazine


def submit_job(db: Session, magazine: CollectionMagazine, worker: Callable[..., None], *args: object) -> None:
    set_progress(magazine.id, "Waiting to start")
    try:
        EXECUTOR.submit(worker, *args)
    except RuntimeError:
        clear_progress(magazine.id)
        logger.exception("Magazine worker is unavailable: %s", magazine.id)
        magazine.status, magazine.phase = "failed", "Worker unavailable"
        magazine.error = "Background processing is unavailable. Your previous edition is unchanged. Retry later."
        db.commit()
        raise HTTPException(503, magazine.error)


@router.get("", response_model=MagazineStatus)
def status(user_tag: str = Depends(user_scope), include_draft: bool = True, db: Session = Depends(get_db)):
    return get_status(db, user_tag, include_draft)


@router.post("/prepare", response_model=MagazineStatus, status_code=202)
def prepare(settings: MagazineSettings, user_tag: str = Depends(user_scope), db: Session = Depends(get_db)):
    if settings.research and not settings.consent:
        raise HTTPException(400, "External research requires explicit cost and data-transfer consent.")
    if not collection_records(db, user_tag):
        raise HTTPException(400, "The selected collection is empty.")
    magazine = db.query(CollectionMagazine).filter_by(user_tag=user_tag).with_for_update().first()
    if magazine is None:
        magazine = CollectionMagazine(user_tag=user_tag, status="draft")
        db.add(magazine)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            magazine = find_magazine(db, user_tag)
    if magazine.status in BUSY:
        return get_status(db, user_tag, include_draft=False)
    token = str(uuid.uuid4())
    magazine.job_token, magazine.status = token, "preparing"
    magazine.phase, magazine.error = "Queued for preparation", None
    db.commit()
    submit_job(db, magazine, run_preparation, magazine.id, token, settings)
    return get_status(db, user_tag, include_draft=False)


@router.put("/draft", response_model=MagazineStatus)
def edit_draft(edits: MagazineDraftEdit, user_tag: str = Depends(user_scope), db: Session = Depends(get_db)):
    magazine = find_magazine(db, user_tag)
    if magazine.status in BUSY:
        raise HTTPException(409, "Wait for the active job or cancel it first.")
    draft = load_payload(magazine.draft_payload)
    if draft is None:
        raise HTTPException(409, "Prepare an editorial draft first.")
    if edits.version != magazine.draft_version:
        raise HTTPException(409, "This draft has changed. Reload it before saving.")
    if len({item.id for item in edits.records}) != len(edits.records) or \
       {item.id for item in edits.records} != {record.id for record in draft.records}:
        raise HTTPException(400, "Draft edits must contain each snapshot record exactly once.")
    by_id = {item.id: item for item in edits.records}
    original_groups = {record.id: record.group for record in draft.records}
    if not edits.preface.strip():
        raise HTTPException(400, "The foreword cannot be blank.")
    draft.preface_manual = draft.preface_manual or edits.preface != draft.settings.preface
    draft.settings.preface = edits.preface
    for record in draft.records:
        edit = by_id[record.id]
        group = " ".join(edit.group.split())
        if not group:
            raise HTTPException(400, "Artist group names cannot be blank.")
        record.group_manual = record.group_manual or group != record.group
        record.description_manual = record.description_manual or edit.description != record.description
        record.group, record.description = group, edit.description
    names = {record.group for record in draft.records}
    old_artists = {artist.name: artist for artist in draft.artists}
    artist_edits = {edit.name: edit for edit in edits.artists}
    if len(artist_edits) != len(edits.artists) or not set(artist_edits).issubset(names | old_artists.keys()):
        raise HTTPException(400, "Invalid artist portrait edits.")
    artists: list[MagazineArtist] = []
    for name in sorted(names, key=str.casefold):
        origins = {original_groups[record.id] for record in draft.records if record.group == name}
        renamed_from = next(iter(origins)) if len(origins) == 1 else None
        if name not in old_artists and renamed_from is not None and renamed_from in old_artists and all(
            record.group == name for record in draft.records if original_groups[record.id] == renamed_from
        ):
            artist = old_artists[renamed_from].model_copy(deep=True, update={"name": name})
            draft.warnings.append(f"Review retained artist portrait after chapter rename: {name}.")
        else:
            artist = old_artists.get(name, MagazineArtist(name=name))
        portrait_edit = artist_edits.get(name)
        if portrait_edit is None and name not in old_artists and renamed_from:
            portrait_edit = artist_edits.get(renamed_from)
        if portrait_edit:
            artist.manual = artist.manual or portrait_edit.portrait != artist.portrait
            artist.portrait = portrait_edit.portrait
        artists.append(artist)
    draft.artists, draft.records = artists, sorted(draft.records, key=record_order)
    magazine.draft_payload = draft.model_dump_json()
    magazine.draft_version += 1
    magazine.status, magazine.error = "draft", None
    magazine.phase = "Ready for editorial review"
    db.commit()
    return get_status(db, user_tag)


@router.post("/publish", response_model=MagazineStatus, status_code=202)
def publish(approval: MagazineApproval, user_tag: str = Depends(user_scope), db: Session = Depends(get_db)):
    magazine = find_magazine(db, user_tag)
    if magazine.status in BUSY:
        return get_status(db, user_tag, include_draft=False)
    if magazine.draft_payload is None:
        raise HTTPException(409, "Prepare and review an editorial draft first.")
    if magazine.draft_version != approval.version:
        raise HTTPException(409, "The draft has changed. Review the latest version.")
    token = str(uuid.uuid4())
    magazine.job_token, magazine.status = token, "rendering"
    magazine.phase, magazine.error = "Queued for PDF creation", None
    db.commit()
    submit_job(db, magazine, run_render, magazine.id, token)
    return get_status(db, user_tag, include_draft=False)


@router.post("/cancel", response_model=MagazineStatus)
def cancel(user_tag: str = Depends(user_scope), db: Session = Depends(get_db)):
    magazine = find_magazine(db, user_tag)
    if magazine.status in BUSY:
        magazine.status, magazine.phase = "cancelled", "Cancelled; previous edition unchanged"
        magazine.job_token = str(uuid.uuid4())
        db.commit()
    return get_status(db, user_tag)


@router.get("/pdf")
def pdf(user_tag: str = Depends(user_scope), download: bool = False, db: Session = Depends(get_db)):
    magazine = find_magazine(db, user_tag)
    if magazine.current_pdf is None:
        raise HTTPException(404, "No completed PDF exists for this user.")
    path = magazine_directory(magazine.id) / magazine.current_pdf
    if not path.is_file():
        logger.error("Stored magazine PDF is missing: %s", magazine.id)
        raise HTTPException(410, "The stored PDF is missing. Please update the magazine.")
    return FileResponse(path, media_type="application/pdf", filename=f"phonox-magazine-edition-{magazine.edition}.pdf",
                        content_disposition_type="attachment" if download else "inline",
                        headers={"Cache-Control": "private, no-store"})


@router.get("/images/{image_id}")
def image(image_id: str, user_tag: str = Depends(user_scope), db: Session = Depends(get_db)):
    magazine = find_magazine(db, user_tag)
    payloads = [load_payload(magazine.draft_payload), load_payload(magazine.current_payload)]
    for payload in payloads:
        if payload:
            for record in payload.records:
                for photo in record.images:
                    if photo.id == image_id and photo.asset:
                        path = asset_path(magazine.id, photo.asset)
                        if path.is_file():
                            return FileResponse(path, media_type="image/jpeg",
                                                headers={"Cache-Control": "private, no-store"})
    raise HTTPException(404, "No snapshot image exists for this user.")


@router.delete("", status_code=204)
def delete(user_tag: str = Depends(user_scope), db: Session = Depends(get_db)):
    magazine = find_magazine(db, user_tag)
    if magazine.status in BUSY:
        raise HTTPException(409, "Cancel the active job before deleting the magazine.")
    magazine_id = magazine.id
    db.delete(magazine)
    db.commit()
    try:
        delete_magazine_files(magazine_id)
    except OSError:
        logger.exception("Magazine deleted but stored file cleanup failed: %s", magazine_id)
        raise HTTPException(500, "The magazine entry was deleted, but file cleanup failed. Check server logs.")
