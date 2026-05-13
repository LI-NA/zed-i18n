from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class ProjectConfig:
    zed_version: str
    zed_repository: str
    cache_dir: Path
    zed_commit: str | None = None


def load_project_config(root: Path) -> ProjectConfig:
    config_path = root / "config" / "project.toml"
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    return ProjectConfig(
        zed_version=data["zed_version"],
        zed_repository=data["zed_repository"],
        cache_dir=Path(data["cache_dir"]),
        zed_commit=data.get("zed_commit"),
    )


def zed_checkout_path(root: Path, config: ProjectConfig) -> Path:
    return root / config.cache_dir / config.zed_version


def zed_clean_extract_checkout_path(root: Path, config: ProjectConfig) -> Path:
    return root / config.cache_dir / f"{config.zed_version}-clean-extract"
