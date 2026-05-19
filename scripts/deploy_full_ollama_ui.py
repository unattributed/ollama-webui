#!/usr/bin/env python3
"""
Install or remove the Ollama Web UI from a local project checkout.

The installer copies the real project files instead of embedding stale placeholder
copies. It deliberately excludes Git metadata, virtual environments, caches,
logs, and packaged archives.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

DEFAULT_SOURCE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_TARGET_DIR = Path.home() / "ollama-webui"
EXCLUDED_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
EXCLUDED_SUFFIXES = {
    ".bak",
    ".log",
    ".pyc",
    ".pyo",
    ".tar",
    ".gz",
    ".zip",
}


def should_exclude(path: Path) -> bool:
    """Return True when a path should not be copied into the install tree."""
    if any(part in EXCLUDED_NAMES for part in path.parts):
        return True

    if path.name.endswith("~"):
        return True

    return any(path.name.endswith(suffix) for suffix in EXCLUDED_SUFFIXES)


def copy_project(source_dir: Path, target_dir: Path, dry_run: bool, verbose: bool) -> None:
    """Copy project files from source_dir to target_dir."""
    source_dir = source_dir.resolve()
    target_dir = target_dir.expanduser().resolve()

    if not source_dir.is_dir():
        raise SystemExit(f"source directory does not exist: {source_dir}")

    required_files = ["index.html", "style.css", "script.js", "models.json", "requirements.txt"]
    missing_files = [name for name in required_files if not (source_dir / name).is_file()]
    if missing_files:
        raise SystemExit(f"source directory is missing required files: {', '.join(missing_files)}")

    if dry_run:
        print(f"[dry-run] would install from {source_dir} to {target_dir}")
    else:
        target_dir.mkdir(parents=True, exist_ok=True)

    for source_path in sorted(source_dir.rglob("*")):
        relative_path = source_path.relative_to(source_dir)
        if should_exclude(relative_path):
            continue

        target_path = target_dir / relative_path
        if source_path.is_dir():
            if dry_run:
                if verbose:
                    print(f"[dry-run] would create directory {target_path}")
            else:
                target_path.mkdir(parents=True, exist_ok=True)
            continue

        if source_path.is_file():
            if dry_run:
                print(f"[dry-run] would copy {relative_path}")
            else:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target_path)
                if verbose:
                    print(f"copied {relative_path}")

    print(f"installed Ollama Web UI at: {target_dir}" if not dry_run else "dry run complete")


def remove_project(target_dir: Path, dry_run: bool) -> None:
    """Remove the installed project directory."""
    target_dir = target_dir.expanduser().resolve()

    if not target_dir.exists():
        print(f"nothing to remove: {target_dir}")
        return

    if dry_run:
        print(f"[dry-run] would remove {target_dir}")
        return

    shutil.rmtree(target_dir)
    print(f"removed Ollama Web UI from: {target_dir}")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Install or remove the Ollama Web UI.")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--install", action="store_true", help="Install the Web UI")
    action.add_argument("--uninstall", action="store_true", help="Uninstall the Web UI")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE_DIR, help="Project source directory")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET_DIR, help="Install target directory")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without changing files")
    parser.add_argument("--verbose", action="store_true", help="Show copied files")
    return parser.parse_args()


def main() -> None:
    """Run the installer or uninstaller."""
    args = parse_args()

    if args.install:
        copy_project(args.source, args.target, args.dry_run, args.verbose)
    elif args.uninstall:
        remove_project(args.target, args.dry_run)


if __name__ == "__main__":
    main()
