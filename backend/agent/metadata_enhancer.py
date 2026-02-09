"""
Intelligent metadata enhancement for vinyl records.

This module provides functions to intelligently enhance existing vinyl record metadata
with new information from additional image analysis.

Instead of re-analyzing all images, we:
1. Analyze only NEW images
2. Extract NEW metadata from them
3. Compare with existing metadata
4. Intelligently merge/enhance using Claude
5. Only update fields with high-confidence new information
"""

import logging
import json
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class MetadataEnhancer:
    """Intelligent metadata enhancement using Claude."""

    def __init__(self):
        """Initialize with Anthropic client."""
        self.client = Anthropic()

    def enhance_metadata(
        self,
        existing_metadata: Dict[str, Any],
        new_metadata: Dict[str, Any],
        existing_confidence: float = 0.5,
    ) -> Tuple[Dict[str, Any], float, List[str]]:
        """
        Intelligently enhance existing metadata with new information.

        Uses Claude to merge metadata with conflict resolution and confidence tracking.

        Args:
            existing_metadata: Current metadata (artist, title, year, label, genres, etc.)
            new_metadata: New metadata extracted from additional images
            existing_confidence: Current confidence level (0.0-1.0)

        Returns:
            Tuple of (enhanced_metadata, new_confidence, changes_made)
        """
        if not new_metadata:
            return existing_metadata, existing_confidence, []

        # Build context for Claude
        enhancement_prompt = f"""You are a vinyl record metadata expert. Your task is to intelligently merge new metadata discoveries with existing record information.

EXISTING METADATA (from previous analysis):
{json.dumps(existing_metadata, indent=2, default=str)}

NEW METADATA (from additional images):
{json.dumps(new_metadata, indent=2, default=str)}

TASK: Analyze both metadata sets and produce an enhanced metadata object with:
1. ONLY fields that should be updated (where new info is better/more certain)
2. A confidence score for each field (0.0-1.0)
3. Explanation for changes

RULES FOR MERGING:
- Artist/Title: Only update if new data is EXACTLY the same (spelling, case, capitalization)
- Year: Only update if existing is missing AND new is present
- Label: Only update if existing is missing AND new is present
- Catalog Number: Keep existing if present, add new if different (separate with "/")
- Barcode: Only update if existing is missing AND new is valid (12-13 digits)
- Genres: Merge lists intelligently (avoid duplicates, keep consistent style)
- Condition: If both have condition, use WORST condition (most conservative assessment). Goldmine scale: M, NM, VG+, VG, G+, G, F, P
- Confidence: Calculate overall confidence based on agreement level

IMPORTANT: Be CONSERVATIVE - only enhance if you're confident (>0.80) the new data is correct.
If there are conflicts, prefer the existing data (it was already verified).

Return ONLY a valid JSON object with this structure:
{{{{
    "enhanced_metadata": {{{{
        "artist": "value or null",
        "title": "value or null",
        "year": null,
        "label": "value or null",
        "catalog_number": "value or null",
        "barcode": "value or null",
        "genres": ["genre1", "genre2"] or null,
        "condition": "Near Mint (NM)" or null,
        "condition_notes": "description of wear" or null
    }}}},
    "field_confidences": {{{{
        "artist": 0.95,
        "title": 0.95,
        "year": 0.8,
        "label": 0.85,
        "catalog_number": 0.9,
        "barcode": 0.85,
        "genres": 0.75,
        "condition": 0.8
    }}}},
    "overall_confidence": 0.87,
    "changes": [
        "Field: explanation of what changed and why",
        "..."
    ]
}}}}

Focus on HIGH CONFIDENCE enhancements only."""

        try:
            logger.info("Calling Claude for intelligent metadata enhancement")
            enhancement_model = os.getenv("ANTHROPIC_ENHANCEMENT_MODEL", "claude-opus-4-1-20250805")

            response = self.client.messages.create(
                model=enhancement_model,
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": enhancement_prompt,
                    }
                ],
            )

            response_text = response.content[0].text

            # Parse JSON response
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                start_idx = response_text.find("{")
                end_idx = response_text.rfind("}") + 1
                if start_idx >= 0 and end_idx > start_idx:
                    result = json.loads(response_text[start_idx:end_idx])
                else:
                    logger.error(f"Failed to parse Claude response: {response_text[:500]}")
                    return existing_metadata, existing_confidence, []

            # Extract enhanced metadata
            enhanced = result.get("enhanced_metadata", {})
            field_confidences = result.get("field_confidences", {})
            overall_confidence = result.get("overall_confidence", existing_confidence)
            changes = result.get("changes", [])

            # Merge with existing metadata (only update non-null new values)
            merged_metadata = existing_metadata.copy()
            applied_changes = []

            for field, value in enhanced.items():
                if value is not None and value != existing_metadata.get(field):
                    merged_metadata[field] = value
                    confidence = field_confidences.get(field, 0.7)
                    applied_changes.append(f"{field}: {changes[0] if changes else 'Updated'} (confidence: {confidence:.0%})")

            # Calculate new overall confidence
            # Boost confidence if metadata was consistent between old and new
            consistency_bonus = 0.05 if applied_changes else 0.10
            new_confidence = min(1.0, (existing_confidence + overall_confidence) / 2 + consistency_bonus)

            logger.info(f"Enhanced metadata with {len(applied_changes)} changes. New confidence: {new_confidence:.2f}")

            return merged_metadata, new_confidence, applied_changes

        except Exception as e:
            logger.error(f"Error enhancing metadata: {e}")
            return existing_metadata, existing_confidence, []

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
