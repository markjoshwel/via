#!/usr/bin/env python3

"""
via helper CLI for local development tasks.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import re
import subprocess
import sys
from typing import Final, TextIO


ROOT: Final[Path] = Path(__file__).resolve().parent.parent
VIA_CONFIG_PATH: Final[Path] = ROOT / "via.toml"
ENTRYPOINT_PATH: Final[Path] = ROOT / "src" / "entry.py"
CONFIG_TOML_PATTERN: Final[re.Pattern[str]] = re.compile(
    r'CONFIG_TOML: Final\[str\] = """\n.*?\n"""',
    re.DOTALL,
)
USAGE = "usage: via <selfcheck|check|sync|deploy|dev> [args...]"


def run(command: Sequence[str]) -> int:
    """Run a command in the repository root and return its exit code."""

    completed = subprocess.run(command, cwd=ROOT, check=False)
    return completed.returncode


def run_all(commands: Sequence[Sequence[str]]) -> int:
    """Run commands in order, stopping at the first failure."""

    for command in commands:
        code = run(command)
        if code != 0:
            return code
    return 0


def sync_bundled_config() -> int:
    """Update src/entry.py bundled CONFIG_TOML from via.toml."""

    config_text = VIA_CONFIG_PATH.read_text(encoding="utf-8").strip("\n")
    entry_text = ENTRYPOINT_PATH.read_text(encoding="utf-8")
    replacement = f'CONFIG_TOML: Final[str] = """\n{config_text}\n"""'
    updated, count = CONFIG_TOML_PATTERN.subn(replacement, entry_text, count=1)
    if count != 1:
        print(
            "could not find CONFIG_TOML in src/entry.py",
            file=sys.stderr,
        )
        return 1
    if updated != entry_text:
        _ = ENTRYPOINT_PATH.write_text(updated, encoding="utf-8")
    return 0


def cmd_selfcheck(extra: Sequence[str]) -> int:
    """Run the repository self-check toolchain."""

    if extra:
        print("selfcheck does not accept additional arguments", file=sys.stderr)
        return 2

    return run_all(
        (
            ("uv", "run", "basedpyright", "."),
            ("uv", "run", "ruff", "check", "."),
            ("uv", "run", "mypy", "."),
        )
    )


def cmd_check(extra: Sequence[str]) -> int:
    """Validate via TOML configuration files."""

    if extra:
        print("check does not accept additional arguments", file=sys.stderr)
        return 2

    return run(
        (
            "uv",
            "run",
            "tombi",
            "lint",
            "via.toml",
            "via.template.toml",
            "via.example.toml",
        )
    )


def cmd_sync(extra: Sequence[str]) -> int:
    """Sync via.toml into bundled CONFIG_TOML in src/entry.py."""

    if extra:
        print("sync does not accept additional arguments", file=sys.stderr)
        return 2
    return sync_bundled_config()


def cmd_deploy(extra: Sequence[str]) -> int:
    """Deploy the worker via pywrangler."""

    sync_code = sync_bundled_config()
    if sync_code != 0:
        return sync_code
    return run(("uv", "run", "pywrangler", "deploy", *extra))


def cmd_dev(extra: Sequence[str]) -> int:
    """Start development mode via pywrangler."""

    sync_code = sync_bundled_config()
    if sync_code != 0:
        return sync_code
    return run(("uv", "run", "pywrangler", "dev", *extra))


def print_usage(stream: TextIO = sys.stdout) -> None:
    """Print CLI usage."""

    print(USAGE, file=stream)


def main(argv: Sequence[str] | None = None) -> int:
    """Entrypoint for the via helper CLI."""

    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help", "help"}:
        print_usage()
        return 0

    command = args[0]
    extra = tuple(args[1:])

    if command == "selfcheck":
        return cmd_selfcheck(extra)
    if command == "check":
        return cmd_check(extra)
    if command == "sync":
        return cmd_sync(extra)
    if command == "deploy":
        return cmd_deploy(extra)
    if command == "dev":
        return cmd_dev(extra)

    print(f"unknown command: {command}", file=sys.stderr)
    print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
