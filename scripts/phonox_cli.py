#!/usr/bin/env python3
import argparse
import io
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"
BACKUP_SCRIPT = SCRIPTS_DIR / "backup.sh"
RESTORE_SCRIPT = SCRIPTS_DIR / "restore.sh"
ENV_FILE = ROOT_DIR / ".env"
BACKUPS_DIR = ROOT_DIR / "backups"

ANSI = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "cyan": "\033[36m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "magenta": "\033[35m",
    "red": "\033[31m",
}


def style(text: str, *styles: str) -> str:
    return "".join(ANSI.get(s, "") for s in styles) + text + ANSI["reset"]


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences so text can be rendered in a curses window."""
    return re.sub(r"\033\[[0-9;]*m", "", text)


def pick_menu(title: str, options: list, logo_lines: list = None, status_data: list = None) -> "int | None":
    """Arrow-key navigable menu via curses. Returns selected index or None if cancelled."""
    import curses

    logo_lines   = [strip_ansi(l) for l in (logo_lines   or [])]
    # status_data: list of (text, color_key, bold)
    status_data = status_data or []

    COLOR_KEYS = {}  # filled after curses init

    def _inner(stdscr):
        curses.curs_set(0)
        try:
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_CYAN,    -1)   # header / border
            curses.init_pair(2, curses.COLOR_WHITE,  curses.COLOR_BLUE)  # highlight
            curses.init_pair(3, curses.COLOR_MAGENTA, -1)   # logo
            curses.init_pair(4, curses.COLOR_GREEN,   -1)   # ok
            curses.init_pair(5, curses.COLOR_YELLOW,  -1)   # warn
            curses.init_pair(6, curses.COLOR_RED,     -1)   # err
        except Exception:
            pass

        COLOR_KEYS.update({
            "header":  curses.color_pair(1),
            "ok":      curses.color_pair(4),
            "warn":    curses.color_pair(5),
            "err":     curses.color_pair(6),
            "dim":     curses.A_DIM,
            "default": 0,
        })

        current = 0
        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            row = 0

            # Logo block — magenta bold
            for line in logo_lines:
                if row >= h - 2:
                    break
                try:
                    stdscr.addstr(row, 0, line[: w - 1], curses.color_pair(3) | curses.A_BOLD)
                except curses.error:
                    pass
                row += 1

            # Status block — structured, per-row colour
            for text, color_key, bold in status_data:
                if row >= h - 2:
                    break
                attr = COLOR_KEYS.get(color_key, 0)
                if bold:
                    attr |= curses.A_BOLD
                try:
                    stdscr.addstr(row, 0, strip_ansi(text)[: w - 1], attr)
                except curses.error:
                    pass
                row += 1

            # Separator + title
            try:
                stdscr.addstr(row, 0, ("─" * min(44, w - 1))[: w - 1], curses.color_pair(1))
                row += 1
                stdscr.addstr(row, 0, title[: w - 1], curses.A_BOLD | curses.color_pair(1))
                row += 1
                stdscr.addstr(row, 0, ("─" * min(44, w - 1))[: w - 1], curses.color_pair(1))
                row += 1
            except curses.error:
                pass

            # Menu options
            for i, opt in enumerate(options):
                if row >= h - 2:
                    break
                label = f"  {strip_ansi(opt)}"
                try:
                    if i == current:
                        stdscr.addstr(
                            row, 0,
                            label.ljust(min(50, w - 1))[: w - 1],
                            curses.A_BOLD | curses.color_pair(2),
                        )
                    else:
                        stdscr.addstr(row, 0, label[: w - 1])
                except curses.error:
                    pass
                row += 1

            footer = "\u2191/\u2193 navigate   Enter select   q/Esc cancel"
            try:
                stdscr.addstr(h - 1, 0, footer[: w - 1], curses.A_DIM)
            except curses.error:
                pass

            stdscr.refresh()
            key = stdscr.getch()

            if key == curses.KEY_UP:
                current = (current - 1) % len(options)
            elif key == curses.KEY_DOWN:
                current = (current + 1) % len(options)
            elif key in (curses.KEY_ENTER, 10, 13):
                return current
            elif key in (ord("q"), ord("Q"), 27):  # q or Esc
                return None

    try:
        return curses.wrapper(_inner)
    except KeyboardInterrupt:
        return None


def run(cmd, cwd=ROOT_DIR):
    try:
        result = subprocess.run(cmd, cwd=cwd)
    except KeyboardInterrupt:
        print(style("\n⚠ Interrupted.", "yellow"))
        sys.exit(1)
    if result.returncode != 0:
        sys.exit(result.returncode)


def get_compose_cmd():
    if shutil.which("docker"):
        try:
            subprocess.run(
                ["docker", "compose", "version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return ["docker", "compose"]
        except Exception:
            pass
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    print("Docker Compose not found. Please install Docker.", file=sys.stderr)
    sys.exit(1)


def cmd_install(args):
    print(style("Installing Phonox...", "cyan"))
    
    # Create necessary directories
    print(style("  📁 Creating directories...", "dim"))
    for path in [
        ROOT_DIR / "backups",
        ROOT_DIR / "data" / "uploads",
        ROOT_DIR / "data" / "postgres" / "data",
    ]:
        path.mkdir(parents=True, exist_ok=True)
    print(style("  ✓ Directories created", "green"))
    
    compose = get_compose_cmd()
    
    # Build images
    if not args.skip_build:
        print(style("  🐳 Building Docker images...", "dim"))
        run(compose + ["build"])
        print(style("  ✓ Images built", "green"))
    
    # Start containers and initialize database
    if args.up:
        print(style("  🚀 Starting containers...", "dim"))
        run(compose + ["up", "-d"])
        print(style("  ✓ Containers started", "green"))
        
        # Check database health
        print(style("  📊 Initializing database...", "dim"))
        import time
        time.sleep(5)  # Give database time to start
        check_database_health()
        print(style("  ✓ Database ready", "green"))
        
        print()
        print(style("Installation complete! 🎉", "green"))
        print(style("Access the application at:", "cyan"))
        print(style("  • Frontend: http://localhost:5173", "dim"))
        print(style("  • API Docs: http://localhost:8000/docs", "dim"))
        print(style("  • Health Check: http://localhost:8000/health", "dim"))
    else:
        print(style("Install complete. Run 'phonox-cli start' to launch containers.", "green"))


def cmd_configure(args):
    if not args.anthropic and not args.tavily and not args.vision_model and not args.chat_model:
        print("No changes. Provide --anthropic, --tavily, --vision-model, and/or --chat-model.", file=sys.stderr)
        sys.exit(1)

    existing_lines = []
    existing_map = {}
    if ENV_FILE.exists():
        existing_lines = ENV_FILE.read_text().splitlines()
        for line in existing_lines:
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                existing_map[key] = value

    if args.anthropic:
        existing_map["ANTHROPIC_API_KEY"] = args.anthropic
    if args.tavily:
        existing_map["TAVILY_API_KEY"] = args.tavily
    if args.vision_model:
        existing_map["ANTHROPIC_VISION_MODEL"] = args.vision_model
    if args.chat_model:
        existing_map["ANTHROPIC_CHAT_MODEL"] = args.chat_model

    updated = []
    seen = set()
    for line in existing_lines:
        if "=" in line and not line.strip().startswith("#"):
            key, _ = line.split("=", 1)
            if key in existing_map:
                updated.append(f"{key}={existing_map[key]}")
                seen.add(key)
            else:
                updated.append(line)
        else:
            updated.append(line)

    for key in ("ANTHROPIC_API_KEY", "TAVILY_API_KEY", "ANTHROPIC_VISION_MODEL", "ANTHROPIC_CHAT_MODEL", "ANTHROPIC_AGGREGATION_MODEL", "ANTHROPIC_ENHANCEMENT_MODEL"):
        if key in existing_map and key not in seen:
            updated.append(f"{key}={existing_map[key]}")

    content = "\n".join(updated).rstrip() + "\n"
    ENV_FILE.write_text(content)
    print(f"Wrote {ENV_FILE}")


_CONFIGURE_KEYS = [
    ("ANTHROPIC_API_KEY",           "Anthropic API key",     True),
    ("TAVILY_API_KEY",              "Tavily API key",         True),
    ("ANTHROPIC_VISION_MODEL",      "Vision model",           False),
    ("ANTHROPIC_CHAT_MODEL",        "Chat model",             False),
    ("ANTHROPIC_AGGREGATION_MODEL", "Aggregation model",      False),
    ("ANTHROPIC_ENHANCEMENT_MODEL", "Enhancement model",      False),
]


def _read_env_map():
    """Return dict of key→value from .env (non-comment lines)."""
    m = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                m[k] = v
    return m


def _mask(value: str, is_secret: bool) -> str:
    """Show last 4 chars for secrets, full value for model names."""
    if not value:
        return "(not set)"
    if is_secret:
        return ("*" * (len(value) - 4) + value[-4:]) if len(value) > 4 else "****"
    return value


def cmd_configure_interactive():
    """Arrow-key driven API key / model configuration."""
    pending = _read_env_map()  # working copy — only written on Save

    while True:
        # Build menu labels showing current (pending) values
        labels = []
        for env_key, label, is_secret in _CONFIGURE_KEYS:
            val = pending.get(env_key, "")
            labels.append(f"{label:<28}  {_mask(val, is_secret)}")
        labels += ["Save & apply", "Cancel"]

        idx = pick_menu("Configure API Keys & Models", labels)

        if idx is None or idx == len(_CONFIGURE_KEYS) + 1:  # Cancel / Esc
            print(style("✗ No changes saved.", "dim"))
            return

        if idx == len(_CONFIGURE_KEYS):  # Save & apply
            # Write to .env using the same logic as cmd_configure
            existing_lines = ENV_FILE.read_text().splitlines() if ENV_FILE.exists() else []
            updated, seen = [], set()
            for line in existing_lines:
                if "=" in line and not line.strip().startswith("#"):
                    k, _ = line.split("=", 1)
                    if k in pending:
                        updated.append(f"{k}={pending[k]}")
                        seen.add(k)
                    else:
                        updated.append(line)
                else:
                    updated.append(line)
            for k, _, __ in _CONFIGURE_KEYS:
                if k in pending and k not in seen:
                    updated.append(f"{k}={pending[k]}")
            ENV_FILE.write_text("\n".join(updated).rstrip() + "\n")
            print(style("✓ Configuration saved.", "green"))
            return

        # Edit selected key
        env_key, label, is_secret = _CONFIGURE_KEYS[idx]
        current = pending.get(env_key, "")
        prompt = f"  {label}"
        if current:
            prompt += f" [keep: {_mask(current, is_secret)}]"
        prompt += ": "
        new_val = input(prompt).strip()
        if new_val:
            pending[env_key] = new_val
        # blank → keep existing value (no change)


def cmd_backup(_args):
    if not BACKUP_SCRIPT.exists():
        print("Backup script not found.", file=sys.stderr)
        sys.exit(1)
    run(["bash", str(BACKUP_SCRIPT)])


def cmd_restore(args):
    if not RESTORE_SCRIPT.exists():
        print("Restore script not found.", file=sys.stderr)
        sys.exit(1)
    run(["bash", str(RESTORE_SCRIPT), args.timestamp])


def cmd_restore_interactive():
    """Arrow-key backup selector with confirmation before restore."""
    if not RESTORE_SCRIPT.exists():
        print(style("✗ Restore script not found.", "red"))
        return

    # Collect available backup sets
    timestamps = set()
    for p in BACKUPS_DIR.glob("phonox_db_*.sql"):
        timestamps.add(p.name.replace("phonox_db_", "").replace(".sql", ""))
    for p in BACKUPS_DIR.glob("phonox_uploads_*.tar.gz"):
        timestamps.add(p.name.replace("phonox_uploads_", "").replace(".tar.gz", ""))

    if not timestamps:
        print(style("⚠ No backups found in ", "yellow") + str(BACKUPS_DIR))
        return

    sorted_ts = sorted(timestamps, reverse=True)  # newest first

    def fmt(ts):
        """20260222_221732 → 2026-02-22  22:17:32"""
        try:
            d, t = ts.split("_")
            return f"{d[:4]}-{d[4:6]}-{d[6:]}  {t[:2]}:{t[2:4]}:{t[4:]}"
        except Exception:
            return ts

    labels = [fmt(ts) for ts in sorted_ts] + ["Cancel"]
    idx = pick_menu("Select backup to restore", labels)

    if idx is None or idx == len(sorted_ts):
        return

    selected = sorted_ts[idx]
    print(style(f"⚠  You are about to restore backup: ", "yellow") + style(fmt(selected), "bold"))
    print(style("   This will OVERWRITE the current database and uploads.", "red"))
    confirm = input(style("   Type 'yes' to confirm: ", "bold")).strip().lower()
    if confirm != "yes":
        print(style("✗ Restore cancelled.", "red"))
        return

    run(["bash", str(RESTORE_SCRIPT), selected])


def check_docker_network():
    """Check if Docker network exists and containers can communicate."""
    compose = get_compose_cmd()
    
    # Check if network exists
    try:
        result = subprocess.run(
            ["docker", "network", "ls"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        networks = result.stdout
        if "phonox_phonox_network" not in networks and "phonox_network" not in networks:
            print(
                style("⚠ Warning: ", "yellow")
                + "Docker network not found. Will be recreated on start."
            )
            return False
    except Exception as e:
        print(
            style("⚠ Warning: ", "yellow")
            + f"Could not check Docker network: {e}"
        )
        return False
    
    return True


def check_database_health():
    """Check if database is accessible."""
    compose = get_compose_cmd()
    
    try:
        result = subprocess.run(
            compose + ["ps", "db"],
            cwd=ROOT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        
        if "healthy" in result.stdout.lower():
            print(style("✓ ", "green") + "Database is healthy")
            return True
        elif "up" in result.stdout.lower() and "starting" in result.stdout.lower():
            print(style("⏳ ", "yellow") + "Database is starting...")
            return None  # Still initializing
        else:
            print(
                style("✗ ", "red")
                + "Database is not responding. Running recovery..."
            )
            return False
    except Exception as e:
        print(
            style("✗ ", "red")
            + f"Could not check database health: {e}"
        )
        return False


def cmd_start(_args):
    compose = get_compose_cmd()
    
    # Check network before starting
    check_docker_network()
    
    print(style("\nStarting containers...", "cyan"))
    run(compose + ["up", "-d"])
    
    # Wait a moment for containers to start
    import time
    time.sleep(3)
    
    # Check database health
    print(style("\nChecking database health...", "cyan"))
    health_result = check_database_health()
    
    if health_result is False:
        print(
            style("\n⚠ ", "yellow")
            + "Database may not be ready. Waiting for initialization..."
        )
        # Give DB more time to initialize
        import time
        for i in range(5, 0, -1):
            print(style(f"  Waiting {i}s...", "dim"), end="\r")
            time.sleep(1)
        print("                    ", end="\r")  # Clear the line
        
        # Check again
        health_result = check_database_health()
        if health_result is False:
            print(
                style(
                    "\n⚠ Database still not healthy. ",
                    "red",
                )
                + "Try running: phonox-cli restart"
            )
    
    print(style("\n✓ Containers started successfully", "green"))


def cmd_restart(_args):
    """Stop and start containers with network recovery."""
    import time
    compose = get_compose_cmd()
    
    print(style("Stopping containers...", "cyan"))
    run(compose + ["down"])
    
    print(style("Restarting containers...", "cyan"))
    run(compose + ["up", "-d"])
    
    # Wait for startup
    time.sleep(3)
    
    print(style("\nChecking database health...", "cyan"))
    health = check_database_health()
    
    if health is not True:
        print(style("\n⚠ Database not healthy. Running recovery...", "yellow"))
        subprocess.run(
            compose + ["restart", "db"],
            cwd=ROOT_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for i in range(10, 0, -1):
            print(style(f"  Waiting {i}s for database recovery...", "dim"), end="\r")
            time.sleep(1)
        print(" " * 44, end="\r")  # clear line
        health = check_database_health()
        if health is not True:
            print(style("\n✗ Database recovery failed. Check logs: docker compose logs db", "red"))
            return
    
    print(style("\n✓ Containers restarted successfully", "green"))


def cmd_stop(_args):
    compose = get_compose_cmd()
    run(compose + ["down"])


def db_query(sql: str):
    """Run a SQL statement in the DB container. Returns (stdout, returncode)."""
    compose = get_compose_cmd()
    result = subprocess.run(
        compose + ["exec", "-T", "db", "psql", "-U", "phonox", "phonox", "-t", "-c", sql],
        cwd=ROOT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout, result.returncode


def list_db_users():
    """Return sorted list of non-empty user_tags, or None if DB is unreachable."""
    stdout, rc = db_query(
        "SELECT DISTINCT user_tag FROM vinyl_records "
        "WHERE user_tag IS NOT NULL AND user_tag != '' ORDER BY user_tag;"
    )
    if rc != 0:
        return None
    return [line.strip() for line in stdout.splitlines() if line.strip()]


def cmd_manage_users(_args):
    """Interactive submenu for renaming a user / collection."""
    while True:
        users = list_db_users()
        if users is None:
            print(style("✗ Cannot reach database. Make sure containers are running.", "red"))
            return

        # Print summary before opening curses
        print("\n" + style("Collections in database:", "bold", "cyan"))
        print(style("─" * 44, "dim"))
        if users:
            for u in users:
                count_out, _ = db_query(
                    f"SELECT COUNT(*) FROM vinyl_records WHERE user_tag = '{u}';"
                )
                print(f"  • {style(u, 'cyan')} ({count_out.strip()} record(s))")
        else:
            print(style("  No collections found.", "dim"))
        print()

        sub = pick_menu("User / Collection Management", ["Rename collection", "Back"])

        if sub is None or sub == 1:
            return

        elif sub == 0:  # Rename
            if not users:
                print("No collections to rename.")
                continue
            user_idx = pick_menu("Select collection to rename", users + ["Cancel"])
            if user_idx is None or user_idx == len(users):
                continue
            old = users[user_idx]
            new = input(f"New name for '{old}': ").strip()
            if not new:
                print("No new name provided.")
                continue
            if "'" in old or "'" in new:
                print(style("✗ Collection names cannot contain single quotes.", "red"))
                continue
            if new in users:
                print(style(f"✗ '{new}' already exists.", "yellow"))
                continue
            _, rc = db_query(
                f"UPDATE vinyl_records SET user_tag = '{new}' WHERE user_tag = '{old}';"
            )
            if rc == 0:
                print(style(f"✓ Renamed '{old}' → '{new}'", "green"))
                print(style("  ⚠ Any open browser session using the old name must select the new name.", "yellow"))
            else:
                print(style("✗ Rename failed.", "red"))


def cmd_docs(_args):
    """Start the MkDocs documentation server."""
    import os
    
    venv_path = ROOT_DIR / ".venv"
    mkdocs_cmd = None
    pip_cmd = None
    
    # Check if virtual environment exists
    if venv_path.exists():
        print(style("✓ ", "green") + "Using existing virtual environment (.venv)")
        if sys.platform == "win32":
            mkdocs_cmd = [str(venv_path / "Scripts" / "mkdocs")]
            pip_cmd = [str(venv_path / "Scripts" / "pip")]
        else:
            mkdocs_cmd = [str(venv_path / "bin" / "mkdocs")]
            pip_cmd = [str(venv_path / "bin" / "pip")]
    else:
        # Fall back to system mkdocs
        if shutil.which("mkdocs"):
            print(style("✓ ", "green") + "Using system mkdocs")
            mkdocs_cmd = ["mkdocs"]
            pip_cmd = ["pip"]
        else:
            print(style("ℹ ", "cyan") + "Virtual environment not found and mkdocs not installed globally")
            print(style("  ", "dim") + "Creating virtual environment...")
            
            # Create venv
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
            
            if sys.platform == "win32":
                mkdocs_cmd = [str(venv_path / "Scripts" / "mkdocs")]
                pip_cmd = [str(venv_path / "Scripts" / "pip")]
            else:
                mkdocs_cmd = [str(venv_path / "bin" / "mkdocs")]
                pip_cmd = [str(venv_path / "bin" / "pip")]
    
    # Check and install mkdocs if needed
    if not Path(mkdocs_cmd[0]).exists():
        print(style("ℹ ", "cyan") + "Installing MkDocs and dependencies...")
        run(pip_cmd + ["install", "-r", "requirements-mkdocs.txt"])
    
    print(style("\nStarting MkDocs server...", "cyan"))
    print(style("📚 Documentation: http://localhost:8001", "green"))
    print(style("Press Ctrl+C to stop", "dim"))
    
    try:
        run(mkdocs_cmd + ["serve", "-a", "localhost:8001"])
    except KeyboardInterrupt:
        print(style("\n✓ MkDocs server stopped", "green"))


def get_status_data():
    """
    Return system status as a list of (text, color_key, bold) tuples.
    color_key: 'header' | 'ok' | 'warn' | 'err' | 'dim' | 'default'
    """
    rows = []

    # ── Per-service container status ─────────────────────
    SERVICE_MAP = {
        "frontend": "Frontend",
        "backend":  "Backend",
        "db":       "DB",
    }
    service_status = {k: ("✗", "err") for k in SERVICE_MAP}

    compose = None
    try:
        compose = get_compose_cmd()
    except SystemExit:
        pass

    if compose:
        try:
            result = subprocess.run(
                compose + ["ps"],
                cwd=ROOT_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            for line in result.stdout.strip().splitlines()[1:]:
                if not line.strip():
                    continue
                ll = line.lower()
                for svc_key in SERVICE_MAP:
                    if svc_key in ll:
                        if "up" in ll and "exit" not in ll:
                            service_status[svc_key] = ("✔", "ok")
                        elif "starting" in ll or "health" in ll:
                            service_status[svc_key] = ("⚠", "warn")
                        else:
                            service_status[svc_key] = ("✗", "err")
        except Exception:
            pass

    # ── Network ──────────────────────────────────────────
    network_icon, network_color = "✗", "err"
    try:
        result = subprocess.run(
            ["docker", "network", "ls"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
        )
        if "phonox_phonox_network" in result.stdout or "phonox_network" in result.stdout:
            network_icon, network_color = "✔", "ok"
        else:
            network_icon, network_color = "⚠", "warn"
    except Exception:
        pass

    # ── Backups ───────────────────────────────────────────
    backup_text, backup_color = "none", "warn"
    if BACKUPS_DIR.exists():
        timestamps = set()
        for p in BACKUPS_DIR.glob("phonox_db_*.sql"):
            timestamps.add(p.name.replace("phonox_db_", "").replace(".sql", ""))
        for p in BACKUPS_DIR.glob("phonox_uploads_*.tar.gz"):
            timestamps.add(p.name.replace("phonox_uploads_", "").replace(".tar.gz", ""))
        if timestamps:
            latest = sorted(timestamps)[-1]
            try:
                d, t = latest.split("_")
                backup_text = f"{d[:4]}-{d[4:6]}-{d[6:]}  {t[:2]}:{t[2:4]}"
            except Exception:
                backup_text = latest
            backup_color = "ok"

    # ── Render: header + two info lines ──────────────────
    rows.append(("─" * 6 + "  Status  " + "─" * 6, "dim", False))

    svc_line = "  " + "   ".join(
        f"{svc_label} {service_status[svc_key][0]}"
        for svc_key, svc_label in SERVICE_MAP.items()
    )
    svc_worst = "ok"
    for k in SERVICE_MAP:
        c = service_status[k][1]
        if c == "err":
            svc_worst = "err"
            break
        if c == "warn":
            svc_worst = "warn"
    rows.append((svc_line, svc_worst, False))

    # Line 2: network + backup — worst of all signals
    all_colors = [service_status[k][1] for k in SERVICE_MAP] + [network_color, backup_color]
    overall = "ok"
    for c in all_colors:
        if c == "err":
            overall = "err"
            break
        if c == "warn":
            overall = "warn"
    rows.append((
        f"  Network {network_icon}   Backup {backup_text}",
        overall, False,
    ))

    return rows


def print_logo():
    logo = r"""
 ██████╗ ██╗  ██╗ ██████╗ ███╗   ██╗ ██████╗ ██╗  ██╗
 ██╔══██╗██║  ██║██╔═══██╗████╗  ██║██╔═══██╗╚██╗██╔╝
 ██████╔╝███████║██║   ██║██╔██╗ ██║██║   ██║ ╚███╔╝ 
 ██╔═══╝ ██╔══██║██║   ██║██║╚██╗██║██║   ██║ ██╔██╗ 
 ██║     ██║  ██║╚██████╔╝██║ ╚████║╚██████╔╝██╔╝ ██╗
 ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝
""".rstrip()
    print(style(logo, "magenta", "bold"))
    print(style("Vinyl Intelligence Console", "dim"))


def print_status():
    print("\n" + style("Status", "bold", "cyan"))
    print(style("─" * 44, "dim"))

    compose = None
    try:
        compose = get_compose_cmd()
    except SystemExit:
        compose = None

    if compose:
        try:
            result = subprocess.run(
                compose + ["ps"],
                cwd=ROOT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                print(style("Containers:", "bold"))
                print(result.stdout.strip())
            else:
                print(style("Containers:", "bold"), style("not running or unavailable", "yellow"))
        except Exception:
            print(style("Containers:", "bold"), style("status unavailable", "yellow"))
    else:
        print(style("Containers:", "bold"), style("Docker Compose not available", "red"))

    # Check Docker Network
    try:
        result = subprocess.run(
            ["docker", "network", "ls"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if "phonox_phonox_network" in result.stdout or "phonox_network" in result.stdout:
            network_name = "phonox_phonox_network" if "phonox_phonox_network" in result.stdout else "phonox_network"
            print(
                style("Network:", "bold")
                + " "
                + style(network_name, "green")
            )
        else:
            print(style("Network:", "bold"), style("not found", "yellow"))
    except Exception:
        print(style("Network:", "bold"), style("status unavailable", "yellow"))

    if BACKUPS_DIR.exists():
        db_backups = sorted(BACKUPS_DIR.glob("phonox_db_*.sql"))
        upload_backups = sorted(BACKUPS_DIR.glob("phonox_uploads_*.tar.gz"))
        timestamps = set()
        for path in db_backups:
            timestamps.add(path.name.replace("phonox_db_", "").replace(".sql", ""))
        for path in upload_backups:
            timestamps.add(
                path.name.replace("phonox_uploads_", "").replace(".tar.gz", "")
            )

        if timestamps:
            latest = sorted(timestamps)[-1]
            print(
                style("Backups:", "bold")
                + " "
                + style(f"{len(timestamps)} set(s)", "green")
                + style(f" (latest: {latest})", "dim")
            )
        else:
            print(style("Backups:", "bold"), style("none found", "yellow"))
    else:
        print(style("Backups:", "bold"), style("directory missing", "yellow"))


def main():
    while True:
        if len(sys.argv) == 1:
            # Capture logo for the curses header
            logo_buf = io.StringIO()
            sys.stdout = logo_buf
            print_logo()
            sys.stdout = sys.__stdout__
            logo_lines = logo_buf.getvalue().splitlines()

            status_data = get_status_data()

            MENU_OPTIONS = [
                "Install (build images)",
                "Install + start",
                "Configure API keys",
                "Start containers",
                "Stop containers",
                "Restart containers (with recovery)",
                "Backup",
                "Restore",
                "View documentation (MkDocs)",
                "Manage users / collections",
                "Exit",
            ]
            choice = pick_menu("Phonox CLI", MENU_OPTIONS, logo_lines=logo_lines, status_data=status_data)

            if choice is None or choice == 10:  # Exit or Esc/q
                print("Goodbye.")
                return
            elif choice == 0:
                sys.argv += ["install"]
            elif choice == 1:
                sys.argv += ["install", "--up"]
            elif choice == 2:
                cmd_configure_interactive()
                sys.argv = [sys.argv[0]]
                continue
            elif choice == 3:
                sys.argv += ["start"]
            elif choice == 4:
                sys.argv += ["stop"]
            elif choice == 5:
                sys.argv += ["restart"]
            elif choice == 6:
                sys.argv += ["backup"]
            elif choice == 7:
                cmd_restore_interactive()
                sys.argv = [sys.argv[0]]
                continue
            elif choice == 8:
                sys.argv += ["docs"]
            elif choice == 9:
                sys.argv += ["manage-users"]

        # Parse and execute command
        parser = argparse.ArgumentParser(prog="phonox-cli")
        subparsers = parser.add_subparsers(dest="command", required=False)

        install = subparsers.add_parser("install", help="Prepare directories and build images")
        install.add_argument("--skip-build", action="store_true", help="Skip docker build")
        install.add_argument("--up", action="store_true", help="Start containers after build")
        install.set_defaults(func=cmd_install)

        configure = subparsers.add_parser("configure", help="Write configuration to .env")
        configure.add_argument("--anthropic", help="Set ANTHROPIC_API_KEY")
        configure.add_argument("--tavily", help="Set TAVILY_API_KEY")
        configure.add_argument("--vision-model", help="Set ANTHROPIC_VISION_MODEL (e.g., claude-sonnet-4-5-20250929)")
        configure.add_argument("--chat-model", help="Set ANTHROPIC_CHAT_MODEL (e.g., claude-haiku-4-5-20251001)")
        configure.set_defaults(func=cmd_configure)

        backup = subparsers.add_parser("backup", help="Backup database and uploads")
        backup.set_defaults(func=cmd_backup)

        restore = subparsers.add_parser("restore", help="Restore database and uploads")
        restore.add_argument("timestamp", help="Backup timestamp to restore")
        restore.set_defaults(func=cmd_restore)

        start = subparsers.add_parser("start", help="Start Docker containers")
        start.set_defaults(func=cmd_start)

        restart = subparsers.add_parser("restart", help="Restart Docker containers with network recovery")
        restart.set_defaults(func=cmd_restart)

        stop = subparsers.add_parser("stop", help="Stop Docker containers")
        stop.set_defaults(func=cmd_stop)

        docs = subparsers.add_parser("docs", help="Start MkDocs documentation server")
        docs.set_defaults(func=cmd_docs)

        manage_users = subparsers.add_parser("manage-users", help="Rename or delete a user / collection")
        manage_users.set_defaults(func=cmd_manage_users)

        try:
            args = parser.parse_args()
            if hasattr(args, 'func'):
                args.func(args)
        except SystemExit:
            pass
        
        # Reset sys.argv and ask for next command
        sys.argv = [sys.argv[0]]
        
        print("\n" + style("─" * 44, "dim"))
        input(style("Press Enter to continue...", "dim"))


if __name__ == "__main__":
    main()
