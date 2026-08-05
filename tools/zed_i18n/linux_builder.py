from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys
import tomllib
from typing import Mapping, Sequence

from tools.zed_i18n.config import load_project_config, zed_checkout_path


CONFIG_PATH = Path("config/linux-builder.toml")
ENVIRONMENT_PATH = Path("docker/linux-builder/environment.toml")
SUPPORTED_PLATFORMS = {"linux/amd64", "linux/arm64"}
IMMUTABLE_REFERENCE_RE = re.compile(r"^(?P<repository>.+)@(?P<digest>sha256:[0-9a-f]{64})$")


@dataclass(frozen=True)
class BuilderConfig:
    image_repository: str
    tag_prefix: str
    context_paths: tuple[str, ...]
    required_platforms: tuple[str, ...]
    glibc_max: Mapping[str, str]


@dataclass(frozen=True)
class BuilderEnvironment:
    ubuntu_base: str
    rust_toolchain: str
    rust_profile: str
    rust_components: tuple[str, ...]
    rust_targets: tuple[str, ...]
    wasi_sdk: str
    uv: str
    python: str


def _read_toml(path: Path) -> dict[str, object]:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except FileNotFoundError as exc:
        raise ValueError(f"missing Linux builder configuration: {path}") from exc


def _string(data: Mapping[str, object], key: str, path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path}: {key} must be a non-empty string")
    return value


def _strings(data: Mapping[str, object], key: str, path: Path) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{path}: {key} must be a non-empty string array")
    return tuple(value)


def load_builder_config(root: Path) -> BuilderConfig:
    path = root / CONFIG_PATH
    data = _read_toml(path)
    required_platforms = _strings(data, "required_platforms", path)
    unsupported = sorted(set(required_platforms) - SUPPORTED_PLATFORMS)
    if unsupported:
        raise ValueError(f"unsupported OCI platform: {', '.join(unsupported)}")
    if len(required_platforms) != len(set(required_platforms)):
        raise ValueError(f"{path}: required_platforms contains duplicates")

    raw_glibc = data.get("glibc_max")
    if not isinstance(raw_glibc, dict):
        raise ValueError(f"{path}: glibc_max must be a table")
    glibc_max = {str(key): str(value) for key, value in raw_glibc.items()}
    for arch in ("x86_64", "aarch64"):
        if not re.fullmatch(r"\d+\.\d+", glibc_max.get(arch, "")):
            raise ValueError(f"{path}: invalid GLIBC limit for {arch}")

    return BuilderConfig(
        image_repository=_string(data, "image_repository", path),
        tag_prefix=_string(data, "tag_prefix", path),
        context_paths=_strings(data, "context_paths", path),
        required_platforms=required_platforms,
        glibc_max=glibc_max,
    )


def load_builder_environment(root: Path) -> BuilderEnvironment:
    path = root / ENVIRONMENT_PATH
    data = _read_toml(path)
    ubuntu_base = _string(data, "ubuntu_base", path)
    if "@sha256:" not in ubuntu_base:
        raise ValueError(f"{path}: ubuntu_base must be digest-pinned")
    return BuilderEnvironment(
        ubuntu_base=ubuntu_base,
        rust_toolchain=_string(data, "rust_toolchain", path),
        rust_profile=_string(data, "rust_profile", path),
        rust_components=_strings(data, "rust_components", path),
        rust_targets=_strings(data, "rust_targets", path),
        wasi_sdk=_string(data, "wasi_sdk", path),
        uv=_string(data, "uv", path),
        python=_string(data, "python", path),
    )


def _context_files(root: Path, configured_paths: Sequence[str]) -> list[Path]:
    resolved_root = root.resolve()
    files: list[Path] = []
    for configured_path in configured_paths:
        path = (root / configured_path).resolve()
        if not path.is_relative_to(resolved_root):
            raise ValueError(f"Linux builder context escapes repository root: {configured_path}")
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(candidate for candidate in path.rglob("*") if candidate.is_file())
        else:
            raise ValueError(f"missing Linux builder context path: {configured_path}")
    return sorted(set(files), key=lambda item: item.relative_to(resolved_root).as_posix())


def compute_context_sha256(root: Path) -> str:
    config = load_builder_config(root)
    resolved_root = root.resolve()
    digest = hashlib.sha256()
    for path in _context_files(root, config.context_paths):
        relative = path.relative_to(resolved_root).as_posix().encode("utf-8")
        contents = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(contents).to_bytes(8, "big"))
        digest.update(contents)
    return digest.hexdigest()


def builder_outputs(root: Path) -> dict[str, str]:
    config = load_builder_config(root)
    environment = load_builder_environment(root)
    context_sha256 = compute_context_sha256(root)
    image_tag = f"{config.tag_prefix}-{context_sha256[:16]}"
    return {
        "image-repository": config.image_repository,
        "image-tag": image_tag,
        "tagged-image": f"{config.image_repository}:{image_tag}",
        "context-sha256": context_sha256,
        "ubuntu-base": environment.ubuntu_base,
        "rust-toolchain": environment.rust_toolchain,
        "rust-profile": environment.rust_profile,
        "rust-components": ",".join(environment.rust_components),
        "rust-targets": ",".join(environment.rust_targets),
        "wasi-sdk": environment.wasi_sdk,
        "uv": environment.uv,
        "python": environment.python,
    }


def resolve_manifest(root: Path, resolved_reference: str, manifest: Mapping[str, object]) -> dict[str, str]:
    config = load_builder_config(root)
    match = IMMUTABLE_REFERENCE_RE.fullmatch(resolved_reference.strip())
    if not match:
        raise ValueError(f"expected immutable image reference, got: {resolved_reference}")
    if match.group("repository") != config.image_repository:
        raise ValueError(f"unexpected image repository: {match.group('repository')}")

    raw_manifests = manifest.get("manifests")
    if not isinstance(raw_manifests, list):
        raise ValueError("builder image must be an OCI image index")

    platforms: list[str] = []
    for descriptor in raw_manifests:
        if not isinstance(descriptor, dict):
            continue
        platform = descriptor.get("platform")
        if not isinstance(platform, dict):
            continue
        os_name = platform.get("os")
        architecture = platform.get("architecture")
        if isinstance(os_name, str) and isinstance(architecture, str):
            platform_name = f"{os_name}/{architecture}"
            platforms.append(platform_name)
            if platform_name in config.required_platforms:
                descriptor_digest = descriptor.get("digest")
                if not isinstance(descriptor_digest, str) or not re.fullmatch(
                    r"sha256:[0-9a-f]{64}", descriptor_digest
                ):
                    raise ValueError(f"invalid descriptor digest for {platform_name}")

    duplicate_platforms = sorted({item for item in platforms if platforms.count(item) > 1})
    if duplicate_platforms:
        raise ValueError(f"duplicate platform descriptors: {', '.join(duplicate_platforms)}")
    missing = sorted(set(config.required_platforms) - set(platforms))
    if missing:
        raise ValueError(f"missing required platforms: {', '.join(missing)}")

    return {
        "image": resolved_reference.strip(),
        "digest": match.group("digest"),
        "platforms": ",".join(config.required_platforms),
    }


def validate_image_labels(root: Path, labels: Mapping[str, object]) -> None:
    environment = load_builder_environment(root)
    expected = {
        "io.zed-i18n.builder.context-sha256": compute_context_sha256(root),
        "io.zed-i18n.builder.rust": environment.rust_toolchain,
        "io.zed-i18n.builder.wasi-sdk": environment.wasi_sdk,
        "io.zed-i18n.builder.uv": environment.uv,
        "io.zed-i18n.builder.python": environment.python,
    }
    for key, value in expected.items():
        if labels.get(key) != value:
            raise ValueError(f"unexpected image label {key}: expected {value!r}, got {labels.get(key)!r}")


def validate_zed_environment(root: Path, zed_root: Path) -> None:
    environment = load_builder_environment(root)
    toolchain_path = zed_root / "rust-toolchain.toml"
    toolchain_data = _read_toml(toolchain_path)
    raw_toolchain = toolchain_data.get("toolchain")
    if not isinstance(raw_toolchain, dict):
        raise ValueError(f"{toolchain_path}: missing toolchain table")

    expected = {
        "rust_toolchain": environment.rust_toolchain,
        "rust_profile": environment.rust_profile,
        "rust_components": tuple(sorted(environment.rust_components)),
        "rust_targets": tuple(sorted(environment.rust_targets)),
    }
    actual = {
        "rust_toolchain": raw_toolchain.get("channel"),
        "rust_profile": raw_toolchain.get("profile"),
        "rust_components": tuple(sorted(raw_toolchain.get("components", []))),
        "rust_targets": tuple(sorted(raw_toolchain.get("targets", []))),
    }
    for field, expected_value in expected.items():
        if actual[field] != expected_value:
            raise ValueError(
                f"Linux builder {field} does not match Zed: "
                f"expected {expected_value!r}, got {actual[field]!r}"
            )

    wasi_path = zed_root / "script" / "download-wasi-sdk"
    try:
        wasi_script = wasi_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"missing Zed WASI SDK script: {wasi_path}") from exc
    wasi_version = None
    for line in wasi_script.splitlines():
        if line.strip().startswith("WASI_SDK_VERSION="):
            wasi_version = line.split("=", 1)[1].strip().strip("\"'")
            break
    if wasi_version != environment.wasi_sdk:
        raise ValueError(
            "Linux builder wasi_sdk does not match Zed: "
            f"expected {environment.wasi_sdk!r}, got {wasi_version!r}"
        )


def _write_outputs(outputs: Mapping[str, str]) -> None:
    for key, value in outputs.items():
        if "\n" in value or "\r" in value:
            raise ValueError(f"GitHub output {key} contains a newline")
        print(f"{key}={value}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve the Linux builder image contract.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("outputs")
    resolve = subparsers.add_parser("resolve-manifest")
    resolve.add_argument("--resolved-reference", required=True)
    subparsers.add_parser("validate-labels")
    validate_zed = subparsers.add_parser("validate-zed")
    validate_zed.add_argument("--zed-root", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "outputs":
        _write_outputs(builder_outputs(args.root))
        return 0

    if args.command == "validate-zed":
        if args.zed_root is None:
            zed_root = zed_checkout_path(args.root, load_project_config(args.root))
        else:
            zed_root = args.zed_root if args.zed_root.is_absolute() else args.root / args.zed_root
        validate_zed_environment(args.root, zed_root)
        print(f"Linux builder environment matches Zed at {zed_root}")
        return 0

    payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        raise ValueError("expected a JSON object on stdin")
    if args.command == "resolve-manifest":
        _write_outputs(resolve_manifest(args.root, args.resolved_reference, payload))
    elif args.command == "validate-labels":
        validate_image_labels(args.root, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
