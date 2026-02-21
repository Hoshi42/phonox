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

    for key in ("ANTHROPIC_API_KEY", "TAVILY_API_KEY", "ANTHROPIC_VISION_MODEL", "ANTHROPIC_CHAT_MODEL"):
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
            print("6) Restart containers (with recovery)")
            print("7) Backup")
            print("8) Restore")
            print("9) View documentation (MkDocs)")
            print("0) Exit")

            choice = input(style("Select an option: ", "bold")).strip()

            if choice == "1":
                sys.argv += ["install"]
            elif choice == "2":
                sys.argv += ["install", "--up"]
            elif choice == "3":
                anthropic = input("ANTHROPIC_API_KEY (leave blank to skip): ").strip()
                tavily = input("TAVILY_API_KEY (leave blank to skip): ").strip()
                vision_model = input("ANTHROPIC_VISION_MODEL (leave blank to skip) [claude-sonnet-4-5-20250929]: ").strip()
                chat_model = input("ANTHROPIC_CHAT_MODEL (leave blank to skip) [claude-haiku-4-5-20251001]: ").strip()
                args = ["configure"]
                if anthropic:
                    args += ["--anthropic", anthropic]
                if tavily:
                    args += ["--tavily", tavily]
                if vision_model:
                    args += ["--vision-model", vision_model]
                if chat_model:
                    args += ["--chat-model", chat_model]
                if len(args) == 1:
                    print("No keys provided. Returning to menu.")
                    continue
                sys.argv += args
            elif choice == "4":
                sys.argv += ["start"]
            elif choice == "5":
                sys.argv += ["stop"]
            elif choice == "6":
                sys.argv += ["restart"]
            elif choice == "7":
                sys.argv += ["backup"]
            elif choice == "8":
                timestamp = input("Backup timestamp to restore: ").strip()
                if not timestamp:
                    print("No timestamp provided. Returning to menu.")
                    continue
                sys.argv += ["restore", timestamp]
            elif choice == "9":
                sys.argv += ["docs"]
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
