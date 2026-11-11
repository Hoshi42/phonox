"""
Metadata merging for vinyl records.

Merges existing record metadata (a stored record or an external source such as Discogs)
with newly extracted metadata (image analysis) using fixed, deterministic rules. The
rules need no LLM call: they are fast, free and reproducible.

Rules (existing data was already verified, so it wins conflicts):
- Artist/Title: keep existing; take new only when existing is missing
- Year/Label: fill only when existing is missing
- Catalog number: keep existing, append a different new one separated by " / "
- Barcode: only with a valid UPC/EAN check digit; replaces a missing or invalid one
- Genres: union, existing first
- Condition: the worst of both (Goldmine scale), with the matching notes
"""

import difflib
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.agent.barcode_utils import has_valid_check_digit

logger = logging.getLogger(__name__)

# Best to worst (Goldmine)
CONDITION_ORDER = ["M", "NM", "VG+", "VG", "G+", "G", "F", "P"]
_CONDITION_NAMES = {
    "mint": "M",
    "near mint": "NM",
    "very good plus": "VG+",
    "very good": "VG",
    "good plus": "G+",
    "good": "G",
    "fair": "F",
    "poor": "P",
}
_PLACEHOLDERS = {"", "unknown", "n/a", "none", "null"}
_SIMILAR = 0.9
_CONFLICT = 0.85


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, tuple, set, dict)):
        return not value
    return str(value).strip().lower() in _PLACEHOLDERS


def _normalize(value: Any) -> str:
    return re.sub(r"[^0-9a-z]", "", str(value or "").lower())


def _similarity(a: Any, b: Any) -> float:
    return difflib.SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def _condition_rank(value: Any) -> Optional[int]:
    """Index into CONDITION_ORDER (higher = worse), or None when not recognisable."""
    text = str(value or "").strip()
    if not text:
        return None
    code = re.search(r"\(([A-Za-z+]+)\)", text)
    candidates = [code.group(1).upper()] if code else []
    candidates.append(text.upper())
    candidates.append(_CONDITION_NAMES.get(re.sub(r"\s*\(.*\)", "", text).strip().lower(), ""))
    for candidate in candidates:
        if candidate in CONDITION_ORDER:
            return CONDITION_ORDER.index(candidate)
    return None


def _merge_catalog(existing: Any, new: Any) -> Optional[str]:
    if _is_missing(new):
        return None if _is_missing(existing) else str(existing)
    if _is_missing(existing):
        return str(new)
    existing_norm, new_norm = _normalize(existing), _normalize(new)
    if not new_norm or new_norm in existing_norm:
        return str(existing)
    if existing_norm in new_norm:
        return str(new)
    return f"{existing} / {new}"


def _merge_genres(existing: Any, new: Any) -> List[str]:
    merged: List[str] = []
    seen = set()
    for genre in list(existing or []) + list(new or []):
        key = str(genre).strip().lower()
        if key and key not in seen:
            seen.add(key)
            merged.append(str(genre).strip())
    return merged


class MetadataEnhancer:
    """Deterministic merge of existing and newly extracted record metadata."""

    def enhance_metadata(
        self,
        existing_metadata: Dict[str, Any],
        new_metadata: Dict[str, Any],
        existing_confidence: float = 0.5,
    ) -> Tuple[Dict[str, Any], float, List[str]]:
        """
        Merge new metadata into existing metadata.

        Args:
            existing_metadata: Current metadata (artist, title, year, label, genres, etc.)
            new_metadata: New metadata extracted from images
            existing_confidence: Current confidence level (0.0-1.0)

        Returns:
            Tuple of (merged_metadata, confidence, changes_made)
        """
        if not new_metadata:
            return existing_metadata, existing_confidence, []

        merged = dict(existing_metadata)
        changes: List[str] = []
        bonus = 0.0

        def fill(field: str, value: Any, reason: str) -> None:
            if value is not None and merged.get(field) != value:
                merged[field] = value
                changes.append(f"{field}: {reason} ({value})")

        # Artist/Title: existing wins; disagreement is a conflict, agreement raises confidence
        for field in ("artist", "title"):
            old, new = existing_metadata.get(field), new_metadata.get(field)
            if _is_missing(old):
                if not _is_missing(new):
                    fill(field, new, "filled from new data")
            elif not _is_missing(new):
                similarity = _similarity(old, new)
                if similarity >= _SIMILAR:
                    bonus += 0.03
                elif similarity < _CONFLICT:
                    bonus -= 0.10
                    changes.append(f"{field}: conflict, kept existing '{old}' (new: '{new}')")

        # Year/Label: only fill gaps; agreement raises confidence
        for field in ("year", "label"):
            old, new = existing_metadata.get(field), new_metadata.get(field)
            if _is_missing(old):
                if not _is_missing(new):
                    fill(field, new, "filled from new data")
            elif not _is_missing(new) and _similarity(old, new) >= _SIMILAR:
                bonus += 0.03

        catalog = _merge_catalog(existing_metadata.get("catalog_number"), new_metadata.get("catalog_number"))
        if catalog and catalog != existing_metadata.get("catalog_number"):
            fill("catalog_number", catalog, "added")

        # Barcode: a number that fails the check digit is a misread and never wins
        old_barcode, new_barcode = existing_metadata.get("barcode"), new_metadata.get("barcode")
        if not (old_barcode and has_valid_check_digit(old_barcode)):
            if new_barcode and has_valid_check_digit(new_barcode):
                fill("barcode", new_barcode, "filled from new data")
            elif old_barcode:
                merged["barcode"] = None
                changes.append(f"barcode: dropped invalid {old_barcode}")

        genres = _merge_genres(existing_metadata.get("genres"), new_metadata.get("genres"))
        if genres and genres != list(existing_metadata.get("genres") or []):
            fill("genres", genres, "merged")

        # Condition: the more conservative (worse) assessment, together with its notes
        old_condition, new_condition = existing_metadata.get("condition"), new_metadata.get("condition")
        old_rank, new_rank = _condition_rank(old_condition), _condition_rank(new_condition)
        use_new = (
            not _is_missing(new_condition)
            and (_is_missing(old_condition) or old_rank is None or (new_rank is not None and new_rank > old_rank))
        )
        if use_new:
            fill("condition", new_condition, "worse or first assessment")
            if new_metadata.get("condition_notes"):
                merged["condition_notes"] = new_metadata["condition_notes"]
        elif _is_missing(existing_metadata.get("condition_notes")) and new_metadata.get("condition_notes"):
            merged["condition_notes"] = new_metadata["condition_notes"]

        confidence = max(0.0, min(1.0, existing_confidence + bonus))
        logger.info(f"Merged metadata with {len(changes)} changes. Confidence: {confidence:.2f}")
        return merged, confidence, changes

    def detect_metadata_conflicts(
        self,
        existing_metadata: Dict[str, Any],
        new_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Detect conflicts between existing and new metadata.

        Returns dict with conflicting fields and their values.
        """
        conflicts = {}

        critical_fields = ["artist", "title", "barcode"]
        for field in critical_fields:
            existing_val = str(existing_metadata.get(field) or "").strip().lower()
            new_val = str(new_metadata.get(field) or "").strip().lower()

            if existing_val and new_val and existing_val != new_val:
                conflicts[field] = {
                    "existing": existing_metadata.get(field),
                    "new": new_metadata.get(field),
                }

        return conflicts

    def get_enhancement_summary(self, changes: List[str]) -> str:
        """Generate a human-readable summary of metadata changes."""
        if not changes:
            return "No metadata changes detected."

        summary = "Metadata enhancements made:\n"
        for change in changes[:5]:  # Limit to 5 changes
            summary += f"• {change}\n"

        if len(changes) > 5:
            summary += f"• ... and {len(changes) - 5} more changes"

        return summary
