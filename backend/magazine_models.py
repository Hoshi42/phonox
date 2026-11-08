"""Validated magazine snapshots, editorial drafts and API contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MagazineSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(default="My Vinyl Collection", min_length=1, max_length=200)
    subtitle: str = Field(default="", max_length=300)
    display_name: str = Field(default="", max_length=100)
    preface: str = Field(default="", max_length=12000)
    cover_image_id: str | None = None
    include_notes: bool = False
    research: bool = True
    refresh_values: bool = True
    consent: bool = False


class MagazineSource(BaseModel):
    title: str
    url: str
    accessed_at: str


class MagazineImage(BaseModel):
    id: str
    filename: str
    asset: str | None = None
    width: int = 0
    height: int = 0
    primary: bool = False
    signature: str = ""


class MagazineRecord(BaseModel):
    id: str
    artist: str | None = None
    group: str
    title: str | None = None
    year: int | None = None
    label: str | None = None
    catalog_number: str | None = None
    barcode: str | None = None
    genres: list[str] = Field(default_factory=list)
    condition: str | None = None
    notes: str | None = None
    stored_value: float | None = None
    images: list[MagazineImage] = Field(default_factory=list)
    fingerprint: str
    description: str = ""
    description_manual: bool = False
    group_manual: bool = False
    value_eur: float | None = None
    value_kind: Literal["stored", "researched", "unavailable"] = "unavailable"
    valued_at: str | None = None
    valuation_note: str = ""
    sources: list[MagazineSource] = Field(default_factory=list)


class MagazineArtist(BaseModel):
    name: str
    portrait: str
    manual: bool = False
    researched: bool = False
    sources: list[MagazineSource] = Field(default_factory=list)


class MagazineDraft(BaseModel):
    settings: MagazineSettings
    snapshot_at: str
    records: list[MagazineRecord]
    artists: list[MagazineArtist]
    warnings: list[str] = Field(default_factory=list)
    steps_used: int = 0
    estimated_cost_eur: float = 0
    preface_manual: bool = False


class MagazineChanges(BaseModel):
    added: int = 0
    changed: int = 0
    removed: int = 0


class MagazineStatus(BaseModel):
    id: str | None = None
    user_tag: str
    status: str = "not_created"
    phase: str = ""
    error: str | None = None
    edition: int = 0
    page_count: int = 0
    record_count: int = 0
    published_at: datetime | None = None
    has_pdf: bool = False
    draft_version: int = 0
    changes: MagazineChanges = Field(default_factory=MagazineChanges)
    draft: MagazineDraft | None = None
    settings: MagazineSettings = Field(default_factory=MagazineSettings)
    research_step_limit: int = 20
    estimated_cost_eur: float = 0
    warnings: list[str] = Field(default_factory=list)


class MagazineRecordEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    group: str = Field(min_length=1, max_length=255)
    description: str = Field(max_length=12000)


class MagazineArtistEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    portrait: str = Field(max_length=12000)


class MagazineDraftEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int
    preface: str = Field(max_length=12000)
    records: list[MagazineRecordEdit]
    artists: list[MagazineArtistEdit]


class MagazineApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int
