#!/usr/bin/env python3
import argparse
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


def run(cmd, cwd=ROOT_DIR):
    result = subprocess.run(cmd, cwd=cwd)
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
    for path in [
        ROOT_DIR / "backups",
        ROOT_DIR / "data" / "uploads",
        ROOT_DIR / "data" / "postgres" / "data",
    ]:
        path.mkdir(parents=True, exist_ok=True)

    compose = get_compose_cmd()
    if not args.skip_build:
        run(compose + ["build"])
    if args.up:
        run(compose + ["up", "-d"])

    print("Install complete.")


def cmd_configure(args):
    if not args.anthropic and not args.tavily:
        print("No changes. Provide --anthropic and/or --tavily.", file=sys.stderr)
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

    for key in ("ANTHROPIC_API_KEY", "TAVILY_API_KEY"):
        if key in existing_map and key not in seen:
            updated.append(f"{key}={existing_map[key]}")

    content = "\n".join(updated).rstrip() + "\n"
    ENV_FILE.write_text(content)
    print(f"Wrote {ENV_FILE}")


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


def cmd_start(_args):
    compose = get_compose_cmd()
    run(compose + ["up", "-d"])


def cmd_stop(_args):
    compose = get_compose_cmd()
    run(compose + ["down"])


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
    print_logo()
    
    while True:
        print_status()
        
        if len(sys.argv) == 1:
            print("\n" + style("Menu", "bold", "cyan"))
            print(style("─" * 44, "dim"))
            print("1) Install (build images)")
            print("2) Install + start")
            print("3) Configure API keys")
            print("4) Start containers")
            print("5) Stop containers")
            print("6) Backup")
            print("7) Restore")
            print("0) Exit")

            choice = input(style("Select an option: ", "bold")).strip()

            if choice == "1":
                sys.argv += ["install"]
            elif choice == "2":
                sys.argv += ["install", "--up"]
            elif choice == "3":
                anthropic = input("ANTHROPIC_API_KEY (leave blank to skip): ").strip()
                tavily = input("TAVILY_API_KEY (leave blank to skip): ").strip()
                args = ["configure"]
                if anthropic:
                    args += ["--anthropic", anthropic]
                if tavily:
                    args += ["--tavily", tavily]
                if len(args) == 1:
                    print("No keys provided. Returning to menu.")
                    continue
                sys.argv += args
            elif choice == "4":
                sys.argv += ["start"]
            elif choice == "5":
                sys.argv += ["stop"]
            elif choice == "6":
                sys.argv += ["backup"]
            elif choice == "7":
                timestamp = input("Backup timestamp to restore: ").strip()
                if not timestamp:
                    print("No timestamp provided. Returning to menu.")
                    continue
                sys.argv += ["restore", timestamp]
            elif choice == "0":
                print("Goodbye.")
                return
            else:
                print("Invalid choice. Please try again.")
                continue

        # Parse and execute command
        parser = argparse.ArgumentParser(prog="phonox-cli")
        subparsers = parser.add_subparsers(dest="command", required=False)

        install = subparsers.add_parser("install", help="Prepare directories and build images")
        install.add_argument("--skip-build", action="store_true", help="Skip docker build")
        install.add_argument("--up", action="store_true", help="Start containers after build")
        install.set_defaults(func=cmd_install)

        configure = subparsers.add_parser("configure", help="Write API keys to .env")
        configure.add_argument("--anthropic", help="Set ANTHROPIC_API_KEY")
        configure.add_argument("--tavily", help="Set TAVILY_API_KEY")
        configure.set_defaults(func=cmd_configure)

        backup = subparsers.add_parser("backup", help="Backup database and uploads")
        backup.set_defaults(func=cmd_backup)

        restore = subparsers.add_parser("restore", help="Restore database and uploads")
        restore.add_argument("timestamp", help="Backup timestamp to restore")
        restore.set_defaults(func=cmd_restore)

        start = subparsers.add_parser("start", help="Start Docker containers")
        start.set_defaults(func=cmd_start)

        stop = subparsers.add_parser("stop", help="Stop Docker containers")
        stop.set_defaults(func=cmd_stop)

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
