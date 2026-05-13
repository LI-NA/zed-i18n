from __future__ import annotations

from pathlib import Path
import subprocess

from .config import ProjectConfig


def ensure_inside_workspace(root: Path, path: Path) -> Path:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"path is outside workspace: {path}") from exc
    return resolved_path


def build_clone_command(config: ProjectConfig, checkout_path: Path) -> list[str]:
    return [
        "git",
        "clone",
        "--branch",
        config.zed_version,
        "--depth",
        "1",
        config.zed_repository,
        str(checkout_path),
    ]


def verify_checkout_revision(config: ProjectConfig, checkout_path: Path) -> None:
    if not config.zed_commit:
        return

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=checkout_path,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    actual = result.stdout.strip()
    if actual != config.zed_commit:
        raise ValueError(
            f"expected Zed {config.zed_version} at {config.zed_commit}, got {actual}"
        )
