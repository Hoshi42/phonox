#!/usr/bin/env python3
# Bootstrap: re-exec under the project venv if sqlalchemy is not importable.
import os as _os, sys as _sys
try:
    import sqlalchemy as _sa_chk  # noqa: F401
except ImportError:
    _venv_py = _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
        ".venv", "bin", "python3",
    )
    if _os.path.exists(_venv_py) and _os.path.realpath(_sys.executable) != _os.path.realpath(_venv_py):
        _os.execv(_venv_py, [_venv_py] + _sys.argv)
    # venv not found or re-exec already happened — give a clear message
    print(
        "Error: 'sqlalchemy' is not installed.\n"
        "  Option 1 – activate the project venv first:\n"
        "    source <repo>/.venv/bin/activate\n"
        "  Option 2 – install the required packages:\n"
        "    pip install sqlalchemy psycopg2-binary pillow",
        file=_sys.stderr,
    )
    _sys.exit(2)

"""
check_integrity.py — Phonox data integrity checker.

Checks consistency between the PostgreSQL database and the uploads directory.

Checks performed:
  1. DB→Disk     : vinyl_images rows whose file_path does not exist on disk
  2. Disk→DB     : Files in uploads dir not referenced by any vinyl_images row
  3. Register    : Records with in_register=TRUE but zero associated images
  4. Broken FK   : vinyl_images.record_id pointing to a non-existent vinyl_records row
  5. MIME type   : stored content_type vs. actual file extension
  6. Corrupt     : files that are zero bytes or cannot be opened as images

Fix actions applied with --fix (single transaction, rolled back on any error):
  Check 1 — Delete orphaned vinyl_images rows.
             If the parent record now has no remaining images and is in the
             register, set in_register=FALSE (it would be invisible anyway).
  Check 2 — Delete orphaned files from disk.
  Check 3 — Set in_register=FALSE for image-less register records.
  Check 4 — Delete orphaned vinyl_images rows + their disk file if present.
  Check 5 — Update content_type in DB to match the actual file extension.
  Check 6 — Delete vinyl_images rows + corrupt/zero-byte files from disk.

Usage:
  python scripts/check_integrity.py
  python scripts/check_integrity.py --db-url postgresql://... --uploads-dir /app/uploads
  python scripts/check_integrity.py --fix
  python scripts/check_integrity.py --output report.txt

Environment variables (used as defaults):
  DATABASE_URL   PostgreSQL connection URL
  UPLOAD_DIR     Path to uploads directory

Exit codes:
  0  No issues found (or all issues fixed successfully)
  1  Issues found (when not using --fix) or unfixed issues remain
  2  Unexpected error (DB connection failure, permission error, etc.)
"""

import argparse
import mimetypes
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ─── ANSI colours ─────────────────────────────────────────────────────────────
CYAN   = "\033[0;36m"
GREEN  = "\033[0;32m"
YELLOW = "\033[1;33m"
RED    = "\033[0;31m"
NC     = "\033[0m"

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


# ─── Report helper ────────────────────────────────────────────────────────────
class Report:
    def __init__(self, output_path: str | None = None, use_color: bool = True):
        self._lines: list[str] = []
        self.output_path = output_path
        self.use_color = use_color
        self.issues = 0
        self.fixes_applied = 0

    # ── formatting helpers ────────────────────────────────────────────────────
    def _c(self, color: str, s: str) -> str:
        return f"{color}{s}{NC}" if self.use_color else s

    def _emit(self, line: str) -> None:
        print(line)
        self._lines.append(_ANSI_RE.sub("", line))

    def header(self, title: str) -> None:
        self._emit(self._c(CYAN, f"\n{'═' * 59}\n  {title}\n{'═' * 59}\n"))

    def section(self, number: int, title: str) -> None:
        self._emit(self._c(CYAN, f"\n{'─' * 59}"))
        self._emit(self._c(CYAN, f"  Check {number} — {title}"))
        self._emit(self._c(CYAN, f"{'─' * 59}"))

    def ok(self, msg: str) -> None:
        self._emit(self._c(GREEN, f"  ✓ {msg}"))

    def issue(self, msg: str, is_warning: bool = False) -> None:
        self.issues += 1
        color, icon = (YELLOW, "!") if is_warning else (RED, "✗")
        self._emit(self._c(color, f"  {icon} {msg}"))

    def fix(self, msg: str) -> None:
        self.fixes_applied += 1
        self._emit(self._c(CYAN, f"    → FIX: {msg}"))

    def info(self, msg: str) -> None:
        self._emit(f"    {msg}")

    def separator(self) -> None:
        self._emit("")

    # ── save to file ─────────────────────────────────────────────────────────
    def save(self) -> None:
        if self.output_path:
            with open(self.output_path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(self._lines) + "\n")


# ─── Utility ──────────────────────────────────────────────────────────────────
def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n //= 1024
    return f"{n:.1f} TB"


def _record_label(artist: str | None, title: str | None, user_tag: str | None = None) -> str:
    label = f"{artist or '?'}: {title or '?'}"
    if user_tag:
        label += f" [{user_tag}]"
    return label


# ─── Core checks ──────────────────────────────────────────────────────────────
def run_checks(conn, uploads_dir: Path, fix: bool, report: Report) -> None:
    # ── fetch all data up front ───────────────────────────────────────────────
    img_rows = conn.execute(text(
        "SELECT vi.id, vi.record_id, vi.file_path, vi.content_type, vi.filename, vi.file_size, "
        "       vr.artist, vr.title, vr.in_register, vr.user_tag "
        "FROM vinyl_images vi "
        "LEFT JOIN vinyl_records vr ON vr.id = vi.record_id"
    )).fetchall()

    register_records = conn.execute(text(
        "SELECT vr.id, vr.artist, vr.title, vr.user_tag, COUNT(vi.id) AS image_count "
        "FROM vinyl_records vr "
        "LEFT JOIN vinyl_images vi ON vi.record_id = vr.id "
        "WHERE vr.in_register = TRUE "
        "GROUP BY vr.id, vr.artist, vr.title, vr.user_tag"
    )).fetchall()

    record_ids = {
        r[0] for r in conn.execute(text("SELECT id FROM vinyl_records")).fetchall()
    }

    # paths stored in DB (only rows that actually have a file_path)
    db_paths = {row.file_path for row in img_rows if row.file_path}

    # files actually on disk
    if uploads_dir.exists():
        disk_files = {str(f) for f in uploads_dir.iterdir() if f.is_file()}
    else:
        disk_files = set()
        report.issue(f"Uploads directory not found: {uploads_dir}", is_warning=True)

    # ── summary ───────────────────────────────────────────────────────────────
    report.info(f"Records in register    : {len(register_records)}")
    report.info(f"Total vinyl_images rows: {len(img_rows)}")
    report.info(f"Files on disk          : {len(disk_files)}")
    report.info(f"Uploads directory      : {uploads_dir}")

    # ─────────────────────────────────────────────────────────────────────────
    # Check 1 — Missing files (DB → disk)
    # ─────────────────────────────────────────────────────────────────────────
    report.section(1, "Missing files (DB → disk)")
    missing = [r for r in img_rows if r.file_path and not Path(r.file_path).exists()]
    if not missing:
        report.ok("All image files referenced in DB exist on disk")
    else:
        for row in missing:
            fname = Path(row.file_path).name
            label = _record_label(row.artist, row.title, row.user_tag)
            report.issue(f"[{row.id[:8]}…] {label} — {fname}  FILE MISSING")
            if fix:
                conn.execute(text("DELETE FROM vinyl_images WHERE id = :id"), {"id": row.id})
                remaining = conn.execute(text(
                    "SELECT COUNT(*) FROM vinyl_images WHERE record_id = :rid"
                ), {"rid": row.record_id}).scalar()
                if remaining == 0 and row.in_register:
                    conn.execute(text(
                        "UPDATE vinyl_records SET in_register = FALSE WHERE id = :id"
                    ), {"id": row.record_id})
                    report.fix("Deleted image row; set record in_register=FALSE (no images remain)")
                else:
                    report.fix(f"Deleted image row ({remaining} image(s) still attached to record)")

    # ─────────────────────────────────────────────────────────────────────────
    # Check 2 — Orphaned files (disk → DB)
    # ─────────────────────────────────────────────────────────────────────────
    report.section(2, "Orphaned files (disk → DB)")
    orphaned = sorted(disk_files - db_paths)
    if not orphaned:
        report.ok("All files on disk are referenced in DB")
    else:
        for fpath in orphaned:
            size = os.path.getsize(fpath)
            report.issue(f"{Path(fpath).name}  ({_human(size)})  — no DB row references this file",
                         is_warning=True)
            if fix:
                os.remove(fpath)
                report.fix(f"Deleted orphaned file: {Path(fpath).name}")

    # ─────────────────────────────────────────────────────────────────────────
    # Check 3 — Register records with no images
    # ─────────────────────────────────────────────────────────────────────────
    report.section(3, "Register records with no images")
    imageless = [r for r in register_records if r.image_count == 0]
    if not imageless:
        report.ok("All register records have at least one image")
    else:
        for row in imageless:
            label = _record_label(row.artist, row.title, row.user_tag)
            report.issue(f"[{row.id[:8]}…] {label} — 0 images")
            if fix:
                conn.execute(text(
                    "UPDATE vinyl_records SET in_register = FALSE WHERE id = :id"
                ), {"id": row.id})
                report.fix("Set in_register=FALSE")

    # ─────────────────────────────────────────────────────────────────────────
    # Check 4 — Broken foreign keys
    # ─────────────────────────────────────────────────────────────────────────
    report.section(4, "Broken foreign keys (vinyl_images → vinyl_records)")
    broken_fk = [r for r in img_rows if r.record_id not in record_ids]
    if not broken_fk:
        report.ok("All vinyl_images rows have a valid parent record")
    else:
        for row in broken_fk:
            report.issue(
                f"[image {row.id[:8]}…] record_id={row.record_id} — PARENT RECORD MISSING"
            )
            if fix:
                conn.execute(text("DELETE FROM vinyl_images WHERE id = :id"), {"id": row.id})
                if row.file_path and Path(row.file_path).exists():
                    os.remove(row.file_path)
                    report.fix("Deleted image row + orphaned file from disk")
                else:
                    report.fix("Deleted image row")

    # ─────────────────────────────────────────────────────────────────────────
    # Check 5 — Content-type mismatches
    # ─────────────────────────────────────────────────────────────────────────
    report.section(5, "Content-type mismatches")
    ct_issues: list[tuple] = []
    for row in img_rows:
        if not row.file_path or not Path(row.file_path).exists():
            continue
        ext = Path(row.file_path).suffix.lower()
        expected_ct, _ = mimetypes.guess_type(f"x{ext}")
        if expected_ct and row.content_type and expected_ct != row.content_type:
            ct_issues.append((row, expected_ct))
    if not ct_issues:
        report.ok("All content-types match file extensions")
    else:
        for row, expected_ct in ct_issues:
            report.issue(
                f"[{row.id[:8]}…] {Path(row.file_path).name}: "
                f"stored={row.content_type}  expected={expected_ct}",
                is_warning=True,
            )
            if fix:
                conn.execute(text(
                    "UPDATE vinyl_images SET content_type = :ct WHERE id = :id"
                ), {"ct": expected_ct, "id": row.id})
                report.fix(f"Updated content_type → {expected_ct}")

    # ─────────────────────────────────────────────────────────────────────────
    # Check 6 — Zero-byte / unreadable files
    # ─────────────────────────────────────────────────────────────────────────
    report.section(6, "Zero-byte / unreadable files")
    try:
        from PIL import Image as PilImage
        pil_available = True
    except ImportError:
        pil_available = False
        report.info("Pillow not available — skipping image readability test (size-only check)")

    corrupt: list[tuple] = []
    for row in img_rows:
        if not row.file_path:
            continue
        p = Path(row.file_path)
        if not p.exists():
            continue
        if p.stat().st_size == 0:
            corrupt.append((row, "zero bytes"))
            continue
        if pil_available:
            try:
                with PilImage.open(str(p)) as img:
                    img.verify()
            except Exception as exc:
                corrupt.append((row, str(exc)))

    if not corrupt:
        report.ok("All files are non-empty and readable")
    else:
        for row, reason in corrupt:
            label = _record_label(row.artist, row.title, row.user_tag)
            report.issue(
                f"[{row.id[:8]}…] {label} — {Path(row.file_path).name}: {reason}"
            )
            if fix:
                conn.execute(text("DELETE FROM vinyl_images WHERE id = :id"), {"id": row.id})
                fp = Path(row.file_path)
                if fp.exists():
                    fp.unlink()
                report.fix("Deleted image row + corrupt file from disk")


# ─── Entry point ──────────────────────────────────────────────────────────────
def main() -> None:
    default_db = os.getenv(
        "DATABASE_URL", "postgresql://phonox:phonox123@localhost:5432/phonox"
    )
    default_uploads = os.getenv(
        "UPLOAD_DIR", str(Path(__file__).parent.parent / "uploads")
    )

    parser = argparse.ArgumentParser(
        description="Phonox data integrity checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--db-url", default=default_db, metavar="URL",
        help="PostgreSQL connection URL (default: $DATABASE_URL)",
    )
    parser.add_argument(
        "--uploads-dir", default=default_uploads, metavar="DIR",
        help="Uploads directory to check (default: $UPLOAD_DIR or <repo>/uploads)",
    )
    parser.add_argument(
        "--fix", action="store_true",
        help=(
            "Apply fixes in a single DB transaction. "
            "Deletes broken rows/files, updates content-types, "
            "sets in_register=FALSE for image-less records."
        ),
    )
    parser.add_argument(
        "--output", metavar="FILE",
        help="Write the report to FILE in addition to stdout",
    )
    args = parser.parse_args()

    use_color = sys.stdout.isatty()
    report = Report(output_path=args.output, use_color=use_color)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report.header(f"Phonox Integrity Report — {timestamp}")
    if args.fix:
        report.info("Mode: CHECK + FIX  (fixes are applied in a single transaction)")
    else:
        report.info("Mode: CHECK ONLY   (run with --fix to apply fixes)")
    report.separator()

    try:
        engine = create_engine(args.db_url, pool_pre_ping=True)
        Session = sessionmaker(bind=engine)
        session = Session()
    except Exception as exc:
        report.issue(f"Could not connect to database: {exc}")
        report.save()
        sys.exit(2)

    try:
        with session.begin():
            run_checks(session, Path(args.uploads_dir).resolve(), fix=args.fix, report=report)
            # transaction is committed automatically if no exception
    except Exception as exc:
        report.issue(f"Unexpected error — transaction rolled back: {exc}")
        report.save()
        sys.exit(2)
    finally:
        session.close()

    # ── final summary ─────────────────────────────────────────────────────────
    report.header("Summary")
    if report.issues == 0:
        report.ok("No issues found — database and uploads are fully consistent")
    else:
        word = "issue" if report.issues == 1 else "issues"
        if args.fix:
            report.info(f"  {report.issues} {word} found, {report.fixes_applied} fix(es) applied")
        else:
            s = "s" if report.issues != 1 else ""
            report.issue(f"{report.issues} {word} found")
            report.info("  Run with --fix to apply automatic fixes")

    report.save()

    if args.output:
        print(f"\n  Report saved to: {args.output}")

    sys.exit(0 if report.issues == 0 else 1)


if __name__ == "__main__":
    main()
