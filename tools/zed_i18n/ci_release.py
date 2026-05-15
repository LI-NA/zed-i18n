from __future__ import annotations

import argparse
from collections import deque
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import tomllib
from typing import Iterable
import zipfile

from .apply import apply_translations
from .config import load_project_config, zed_checkout_path
from .distribution import (
    DistributionConfig,
    apply_distribution_patches,
    distribution_build_env,
    load_distribution_config,
    parse_i18n_revision,
    resolve_update_manifest_url,
)
from .zed_source import ensure_inside_workspace


DEFAULT_UPDATE_EXPLANATION = (
    "Install localized Zed updates from the zed-i18n GitHub Releases page."
)


@dataclass(frozen=True)
class BuildPlatform:
    id: str
    platform: str
    arch: str
    runner: str
    bundle_target: str


@dataclass(frozen=True)
class DiskSummaryEntry:
    label: str
    path: Path
    total_bytes: int
    used_bytes: int
    free_bytes: int


BUILD_PLATFORMS: tuple[BuildPlatform, ...] = (
    BuildPlatform("linux-x86_64", "linux", "x86_64", "ubuntu-24.04", ""),
    BuildPlatform("linux-aarch64", "linux", "aarch64", "ubuntu-24.04-arm", ""),
    BuildPlatform("macos-x86_64", "macos", "x86_64", "macos-15-intel", "x86_64-apple-darwin"),
    BuildPlatform("macos-aarch64", "macos", "aarch64", "macos-15", "aarch64-apple-darwin"),
    BuildPlatform("windows-x86_64", "windows", "x86_64", "windows-2022", ""),
    BuildPlatform("windows-aarch64", "windows", "aarch64", "windows-2022", ""),
)

PLATFORM_BY_ID = {platform.id: platform for platform in BUILD_PLATFORMS}

SIGNING_ENV_VARS = {
    "AZURE_TENANT_ID",
    "AZURE_CLIENT_ID",
    "AZURE_CLIENT_SECRET",
    "ACCOUNT_NAME",
    "CERT_PROFILE_NAME",
    "ENDPOINT",
    "FILE_DIGEST",
    "TIMESTAMP_DIGEST",
    "TIMESTAMP_SERVER",
}

MACOS_TRANSIENT_BUNDLE_ERRORS = (
    "tar: bin/git: Not found in archive",
    "hdiutil: create failed - Resource busy",
)
MACOS_BUNDLE_RETRY_STAGE_MARKERS = (
    "Creating application bundle",
    "Bundled ",
    "Downloading git binary",
    "Creating final DMG",
    "Adding license agreement to DMG",
    "Notarizing DMG",
)
STREAMED_COMMAND_TAIL_LINES = 1000


def windows_signing_env_complete(env: dict[str, str]) -> bool:
    return all(env.get(name) for name in SIGNING_ENV_VARS)


def runner_override_env_name(platform_id: str) -> str:
    return f"ZED_I18N_RUNNER_{platform_id.upper().replace('-', '_')}"


def runner_label(platform: BuildPlatform) -> str | list[str]:
    value = os.environ.get(runner_override_env_name(platform.id), "").strip()
    if not value:
        return platform.runner
    if value.startswith("["):
        labels = json.loads(value)
        if not isinstance(labels, list) or not all(isinstance(label, str) for label in labels):
            raise ValueError(f"invalid runner label list for {platform.id}: {value}")
        return labels
    return value


def list_translation_languages(root: Path) -> list[str]:
    translation_dir = root / "translations"
    return sorted(path.stem for path in translation_dir.glob("*.json"))


def split_csv(value: str | None) -> list[str]:
    if value is None:
        return []
    normalized = value.replace("\n", ",").replace(" ", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def select_languages(root: Path, language_spec: str | None) -> list[str]:
    available = list_translation_languages(root)
    if not language_spec or language_spec.lower() == "all":
        return available

    requested = split_csv(language_spec)
    missing = [language for language in requested if language not in available]
    if missing:
        raise ValueError(
            "unknown language(s): "
            + ", ".join(missing)
            + "; available: "
            + ", ".join(available)
        )
    return requested


def select_platforms(platform_spec: str | None) -> list[BuildPlatform]:
    if not platform_spec or platform_spec.lower() == "all":
        return list(BUILD_PLATFORMS)

    selected: list[BuildPlatform] = []
    seen: set[str] = set()
    aliases = {"mac": "macos"}
    by_family: dict[str, list[BuildPlatform]] = {}
    for platform in BUILD_PLATFORMS:
        by_family.setdefault(platform.platform, []).append(platform)

    for item in split_csv(platform_spec):
        item = aliases.get(item, item)
        if item in PLATFORM_BY_ID:
            candidates = [PLATFORM_BY_ID[item]]
        elif item in by_family:
            candidates = by_family[item]
        else:
            raise ValueError(
                f"unknown platform: {item}; available: "
                + ", ".join(platform.id for platform in BUILD_PLATFORMS)
            )

        for candidate in candidates:
            if candidate.id not in seen:
                selected.append(candidate)
                seen.add(candidate.id)

    return selected


def shard_items(items: list[str], shard_size: int) -> list[list[str]]:
    if shard_size <= 0:
        raise ValueError("shard size must be positive")
    return [items[index : index + shard_size] for index in range(0, len(items), shard_size)]


def build_matrix(
    root: Path,
    language_spec: str | None = None,
    platform_spec: str | None = None,
    shard_size: int = 1,
) -> tuple[list[str], list[dict[str, object]]]:
    languages = select_languages(root, language_spec)
    platforms = select_platforms(platform_spec)
    language_shards = shard_items(languages, shard_size)

    rows: list[dict[str, object]] = []
    for platform in platforms:
        for shard_index, shard in enumerate(language_shards, start=1):
            shard_name = shard[0] if shard_size == 1 else f"shard-{shard_index}"
            rows.append(
                {
                    "id": f"{platform.id}-{shard_name}",
                    "platform": platform.platform,
                    "arch": platform.arch,
                    "runner": runner_label(platform),
                    "bundle_target": platform.bundle_target,
                    "languages": ",".join(shard),
                    "artifact": f"zed-i18n-{platform.id}-{shard_name}",
                }
            )
    return languages, rows


def write_github_matrix_outputs(
    root: Path,
    language_spec: str | None,
    platform_spec: str | None,
    shard_size: int,
) -> None:
    for name, value in github_matrix_outputs(root, language_spec, platform_spec, shard_size).items():
        print(f"{name}={value}")


def github_matrix_outputs(
    root: Path,
    language_spec: str | None,
    platform_spec: str | None,
    shard_size: int,
) -> dict[str, str]:
    config = load_project_config(root)
    languages, rows = build_matrix(root, language_spec, platform_spec, shard_size)
    rows_by_platform = {
        platform: [row for row in rows if row["platform"] == platform]
        for platform in ("linux", "macos", "windows")
    }

    outputs = {
        "matrix": github_matrix_json(rows),
        "languages": ",".join(languages),
        "zed-version": config.zed_version,
        "build-count": str(len(rows)),
    }
    for platform, platform_rows in rows_by_platform.items():
        outputs[f"{platform}-matrix"] = github_matrix_json(platform_rows)
        outputs[f"{platform}-build-count"] = str(len(platform_rows))
    return outputs


def github_matrix_json(rows: list[dict[str, object]]) -> str:
    return json.dumps({"include": rows}, separators=(",", ":"))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def reset_zed_checkout(zed_root: Path) -> None:
    subprocess.run(["git", "reset", "--hard"], cwd=zed_root, check=True)


def apply_language(root: Path, zed_root: Path, language: str) -> None:
    manifest = read_json(root / "manifest" / "ui-strings.json")
    translations = read_json(root / "translations" / f"{language}.json")
    report = apply_translations(zed_root, manifest, translations)
    write_json(root / "reports" / f"apply-{language}.json", asdict(report))
    if not report.ok:
        raise RuntimeError(
            f"apply failed for {language}: "
            f"{len(report.missing)} missing translations, {len(report.stale)} stale occurrences"
        )
    print(f"Applied {len(report.applied)} source strings for {language}")


def zed_crate_version(zed_root: Path) -> str:
    cargo_toml = zed_root / "crates" / "zed" / "Cargo.toml"
    data = tomllib.loads(cargo_toml.read_text(encoding="utf-8"))
    return data["package"]["version"]


def bundle_env(
    zed_root: Path,
    platform: str,
    distribution: DistributionConfig | None = None,
    language: str | None = None,
    release_tag: str | None = None,
    repository: str | None = None,
) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("CARGO_INCREMENTAL", "0")
    if distribution is None:
        env.setdefault("ZED_UPDATE_EXPLANATION", DEFAULT_UPDATE_EXPLANATION)
    elif language:
        env = distribution_build_env(
            distribution,
            env,
            locale=language,
            release_tag=release_tag,
            repository=repository,
        )
    env.setdefault("RELEASE_VERSION", zed_crate_version(zed_root))
    if platform == "linux":
        env.setdefault("CC", "clang-18")
        env.setdefault("CXX", "clang++-18")
    if platform == "windows" and not windows_signing_env_complete(env):
        env.pop("CI", None)
        print("Windows signing variables are incomplete; building unsigned installer.")
    return env


def bundle_command(platform: str, arch: str, bundle_target: str) -> list[str]:
    if platform == "linux":
        return ["bash", "./script/bundle-linux"]
    if platform == "macos":
        return ["bash", "./script/bundle-mac", bundle_target]
    if platform == "windows":
        return [
            "pwsh",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "script/bundle-windows.ps1",
            "-Architecture",
            arch,
        ]
    raise ValueError(f"unsupported platform: {platform}")


def prepare_windows_bundle_script(zed_root: Path) -> None:
    default_path = (
        r"C:\Program Files\Microsoft Visual Studio\2022\Community"
        r"\Common7\Tools\Launch-VsDevShell.ps1"
    )
    if Path(default_path).exists():
        return

    for edition in ["Enterprise", "Professional", "BuildTools"]:
        candidate = (
            Path(r"C:\Program Files\Microsoft Visual Studio\2022")
            / edition
            / "Common7"
            / "Tools"
            / "Launch-VsDevShell.ps1"
        )
        if candidate.exists():
            script_path = zed_root / "script" / "bundle-windows.ps1"
            script = script_path.read_text(encoding="utf-8")
            script_path.write_text(
                script.replace(default_path, str(candidate)),
                encoding="utf-8",
            )
            print(f"Using Visual Studio developer shell: {candidate}")
            return


def patch_remote_server_build(zed_root: Path, platform: str) -> None:
    if platform == "linux":
        patch_linux_remote_server_build(zed_root / "script" / "bundle-linux")
    elif platform == "macos":
        patch_macos_remote_server_build(zed_root / "script" / "bundle-mac")
    elif platform == "windows":
        patch_windows_remote_server_build(zed_root / "script" / "bundle-windows.ps1")
    else:
        raise ValueError(f"unsupported platform: {platform}")


def patch_linux_remote_server_build(path: Path) -> None:
    script = path.read_text(encoding="utf-8")
    script = script.replace(
        """if "$rustup_installed"; then
    rustup target add "$remote_server_triple"
fi

""",
        "",
    )
    script = script.replace(
        """# Build remote_server in separate invocation to prevent feature unification from other crates
# from influencing dynamic libraries required by it.
if [[ "$remote_server_triple" == "$musl_triple" ]]; then
    export RUSTFLAGS="${RUSTFLAGS:-} -C target-feature=+crt-static"
fi
cargo build --release --target "${remote_server_triple}" --package remote_server

""",
        "",
    )
    script = script.replace(
        ' \\\n                "${target_dir}/${remote_server_triple}"/release/remote_server',
        "",
    )
    script = script.replace(
        'llvm-objcopy --strip-debug "${target_dir}/${remote_server_triple}/release/remote_server"\n',
        "",
    )
    script = re.sub(
        r"\n# Ensure that remote_server does not depend on libssl nor libcrypto, as we got rid of these deps\.\n"
        r"if ldd \"\$\{target_dir\}/\$\{remote_server_triple\}/release/remote_server\" \| grep -q 'libcrypto\\\|libssl'; then\n"
        r"    if \[\[ \"\$remote_server_triple\" == \*-musl \]\]; then\n"
        r"        echo \"Error: remote_server still depends on libssl or libcrypto\" && exit 1\n"
        r"    else\n"
        r"        echo \"Info: Using non-musl remote-server build\.\"\n"
        r"    fi\n"
        r"fi\n",
        "\n",
        script,
    )
    script = re.sub(
        r'^gzip -f --stdout --best "\$\{target_dir\}/\$\{remote_server_triple\}/release/remote_server" > "\$\{target_dir\}/zed-remote-server-linux-\$\{arch\}\.gz"\r?\n',
        "",
        script,
        flags=re.MULTILINE,
    )
    script = "".join(
        line
        for line in script.splitlines(keepends=True)
        if "--package remote_server" not in line
        and "zed-remote-server-linux" not in line
        and 'llvm-objcopy --strip-debug "${target_dir}/${remote_server_triple}/release/remote_server"' not in line
    )
    if "--package remote_server" in script or "zed-remote-server-linux" in script:
        raise ValueError("failed to remove Linux remote_server build steps")
    path.write_text(script, encoding="utf-8")


def patch_macos_remote_server_build(path: Path) -> None:
    script = path.read_text(encoding="utf-8")
    script = script.replace(
        """# Build remote_server in separate invocation to prevent feature unification from other crates
# from influencing dynamic libraries required by it.
cargo build ${build_flag} --package remote_server --target $target_triple

""",
        "",
    )
    script = re.sub(
        r'\n        if ! dsymutil --flat "target/\$\{target_triple\}/\$\{target_dir\}/remote_server" 2> target/dsymutil\.log; then\n'
        r"            echo \"dsymutil failed\"\n"
        r"            cat target/dsymutil\.log\n"
        r"            exit 1\n"
        r"        fi\n",
        "\n",
        script,
    )
    script = script.replace(
        ' \\\n                "target/${target_triple}/${target_dir}/remote_server.dwarf"',
        "",
    )
    script = re.sub(
        r'^sign_binary "target/\$target_triple/release/remote_server"\r?\n',
        "",
        script,
        flags=re.MULTILINE,
    )
    script = re.sub(
        r"^gzip -f --stdout --best target/\$target_triple/release/remote_server > target/zed-remote-server-macos-\$arch_suffix\.gz\r?\n",
        "",
        script,
        flags=re.MULTILINE,
    )
    script = "".join(
        line
        for line in script.splitlines(keepends=True)
        if "--package remote_server" not in line and "zed-remote-server-macos" not in line
    )
    if "--package remote_server" in script or "zed-remote-server-macos" in script:
        raise ValueError("failed to remove macOS remote_server build steps")
    path.write_text(script, encoding="utf-8")


def patch_windows_remote_server_build(path: Path) -> None:
    script = path.read_text(encoding="utf-8")
    script = script.replace(
        """function BuildRemoteServer {
    Write-Output "Building remote_server for $target"
    cargo build --release --package remote_server --target $target

    # Create zipped remote server binary
    $remoteServerSrc = (Resolve-Path ".\\$CargoOutDir\\remote_server.exe").Path

    if ($env:CI) {
        Write-Output "Code signing remote_server.exe"
        & "$innoDir\\sign.ps1" $remoteServerSrc
    }

    $remoteServerDst = "$env:ZED_WORKSPACE\\target\\zed-remote-server-windows-$Architecture.zip"
    Write-Output "Compressing remote_server to $remoteServerDst"
    Compress-Archive -Path $remoteServerSrc -DestinationPath $remoteServerDst -Force

    Write-Output "Remote server compressed successfully"
}

""",
        "",
    )
    script = re.sub(r"^\s*BuildRemoteServer\s*\r?\n", "", script, flags=re.MULTILINE)
    script = re.sub(
        r'(\s*"\.\\\$CargoOutDir\\explorer_command_injector\.pdb"),\r?\n\s*"\.\\\$CargoOutDir\\remote_server\.pdb"',
        r"\1",
        script,
    )
    if re.search(r"^\s*BuildRemoteServer\s*$", script, flags=re.MULTILINE):
        raise ValueError("failed to remove Windows remote_server build invocation")
    path.write_text(script, encoding="utf-8")


def app_source_path(
    zed_root: Path,
    platform: str,
    arch: str,
    distribution: DistributionConfig | None = None,
) -> Path:
    target_dir = cargo_target_dir(zed_root)
    if platform == "linux":
        return target_dir / "release" / f"zed-linux-{arch}.tar.gz"
    if platform == "macos":
        return zed_root / "target" / f"{arch}-apple-darwin" / "release" / f"Zed-{arch}.dmg"
    if platform == "windows":
        if distribution is not None:
            return zed_root / "target" / f"{distribution.windows_setup_name}-{arch}.exe"
        return zed_root / "target" / f"Zed-{arch}.exe"
    raise ValueError(f"unsupported platform: {platform}")


def windows_portable_source_path(
    zed_root: Path,
    arch: str,
    distribution: DistributionConfig | None = None,
) -> Path:
    setup_name = distribution.windows_setup_name if distribution is not None else "Zed"
    return zed_root / "target" / f"{setup_name}-{arch}.zip"


def app_asset_name(language: str, platform: str, arch: str) -> str:
    if platform == "linux":
        return f"zed-i18n-{language}-linux-{arch}.tar.gz"
    if platform == "macos":
        return f"Zed-i18n-{language}-macos-{arch}.dmg"
    if platform == "windows":
        return f"Zed-i18n-{language}-windows-{arch}.exe"
    raise ValueError(f"unsupported platform: {platform}")


def windows_portable_asset_name(language: str, arch: str) -> str:
    return f"Zed-i18n-{language}-windows-{arch}.zip"


def app_asset_names(language: str, platform: str, arch: str) -> list[str]:
    names = [app_asset_name(language, platform, arch)]
    if platform == "windows":
        names.append(windows_portable_asset_name(language, arch))
    return names


def expected_app_asset_names(
    languages: Iterable[str],
    platforms: Iterable[BuildPlatform],
) -> list[str]:
    return sorted(
        name
        for platform in platforms
        for language in languages
        for name in app_asset_names(language, platform.platform, platform.arch)
    )


WINDOWS_PORTABLE_ENTRIES = (
    "Zed.exe",
    "bin",
    "tools",
    "appx",
    "x64",
    "arm64",
    "conpty.dll",
    "amd_ags_x64.dll",
)
WINDOWS_PORTABLE_COMMON_REQUIRED_ENTRIES = (
    "Zed.exe",
    "bin/zed.exe",
    "bin/zed",
    "tools/auto_update_helper.exe",
    "appx/zed_explorer_command_injector.appx",
    "appx/zed_explorer_command_injector.dll",
    "conpty.dll",
)
WINDOWS_PORTABLE_ARCH_REQUIRED_ENTRIES = {
    "x86_64": ("x64/OpenConsole.exe", "arm64/OpenConsole.exe", "amd_ags_x64.dll"),
    "aarch64": ("arm64/OpenConsole.exe",),
}


def windows_portable_required_entries(arch: str) -> tuple[str, ...]:
    if arch not in WINDOWS_PORTABLE_ARCH_REQUIRED_ENTRIES:
        raise ValueError(f"unsupported Windows architecture: {arch}")
    return (
        *WINDOWS_PORTABLE_COMMON_REQUIRED_ENTRIES,
        *WINDOWS_PORTABLE_ARCH_REQUIRED_ENTRIES[arch],
    )


def create_windows_portable_zip(zed_root: Path, arch: str, destination: Path) -> None:
    source_dir = zed_root / "inno" / arch
    if not source_dir.exists():
        raise FileNotFoundError(f"expected Windows bundle payload does not exist: {source_dir}")

    missing = [
        entry
        for entry in windows_portable_required_entries(arch)
        if not (source_dir / entry).exists()
    ]
    if missing:
        raise FileNotFoundError(
            f"expected Windows bundle payload entries are missing: {', '.join(missing)}"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()

    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for entry in WINDOWS_PORTABLE_ENTRIES:
            source = source_dir / entry
            if not source.exists():
                continue
            if source.is_dir():
                for path in sorted(item for item in source.rglob("*") if item.is_file()):
                    archive.write(path, (Path(entry) / path.relative_to(source)).as_posix())
            else:
                archive.write(source, entry)

    print(f"Created Windows portable zip {destination}")


def run_streaming_command(command: list[str], cwd: Path, env: dict[str, str]) -> None:
    tail: deque[str] = deque(maxlen=STREAMED_COMMAND_TAIL_LINES)
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    if process.stdout is not None:
        for line in process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            tail.append(line)

    return_code = process.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command, output="".join(tail))


def called_process_output(error: subprocess.CalledProcessError) -> str:
    output = error.output if error.output is not None else error.stderr
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return str(output)


def macos_bundle_retry_reason(output: str) -> str | None:
    for pattern in MACOS_TRANSIENT_BUNDLE_ERRORS:
        if pattern in output:
            return pattern
    for marker in MACOS_BUNDLE_RETRY_STAGE_MARKERS:
        if marker in output:
            return f"bundle stage reached: {marker}"
    return None


def macos_arch_suffix(bundle_target: str) -> str:
    if bundle_target == "aarch64-apple-darwin":
        return "aarch64"
    if bundle_target == "x86_64-apple-darwin":
        return "x86_64"
    raise ValueError(f"unsupported macOS bundle target: {bundle_target}")


def cleanup_macos_bundle_retry_state(zed_root: Path, bundle_target: str) -> None:
    arch_suffix = macos_arch_suffix(bundle_target)
    dmg_target_directory = zed_root / "target" / bundle_target / "release"
    dmg_source_directory = dmg_target_directory / "dmg"
    dmg_file_path = dmg_target_directory / f"Zed-{arch_suffix}.dmg"
    app_bundle_directory = dmg_target_directory / "bundle" / "osx"

    print("Cleaning macOS bundle state before retry")
    subprocess.run(["hdiutil", "info"], cwd=zed_root, check=False)
    for volume in (Path("/Volumes/Zed"), Path("/Volumes/Zed 1")):
        if volume.exists():
            subprocess.run(["hdiutil", "detach", str(volume), "-force"], cwd=zed_root, check=False)
    shutil.rmtree(dmg_source_directory, ignore_errors=True)
    shutil.rmtree(app_bundle_directory, ignore_errors=True)
    try:
        dmg_file_path.unlink(missing_ok=True)
    except OSError as error:
        print(f"Warning: failed to remove partial DMG before retry: {error}")


def run_bundle_command_with_retry(
    platform: str,
    bundle_target: str,
    command: list[str],
    zed_root: Path,
    env: dict[str, str],
) -> None:
    try:
        run_streaming_command(command, cwd=zed_root, env=env)
    except subprocess.CalledProcessError as error:
        if platform != "macos":
            raise
        retry_reason = macos_bundle_retry_reason(called_process_output(error))
        if retry_reason is None:
            raise

        print(f"Detected retryable macOS bundle failure: {retry_reason}")
        cleanup_macos_bundle_retry_state(zed_root, bundle_target)
        print("Retrying macOS bundle command once")
        time.sleep(10)
        run_streaming_command(command, cwd=zed_root, env=env)


def cargo_target_dir(zed_root: Path) -> Path:
    target_dir = Path(os.environ.get("CARGO_TARGET_DIR", "target"))
    if not target_dir.is_absolute():
        target_dir = zed_root / target_dir
    return target_dir


def nearest_existing_path(path: Path) -> Path:
    resolved = path.resolve()
    while not resolved.exists():
        parent = resolved.parent
        if parent == resolved:
            break
        resolved = parent
    return resolved


def format_gib(byte_count: int) -> str:
    return f"{byte_count / (1024**3):.1f} GiB"


def disk_summary_entries(paths: Iterable[tuple[str, Path]]) -> list[DiskSummaryEntry]:
    entries: list[DiskSummaryEntry] = []
    for label, path in paths:
        probe = nearest_existing_path(path)
        usage = shutil.disk_usage(probe)
        entries.append(
            DiskSummaryEntry(
                label=label,
                path=probe,
                total_bytes=usage.total,
                used_bytes=usage.used,
                free_bytes=usage.free,
            )
        )
    return entries


def print_disk_summary(root: Path, label: str) -> None:
    paths = [("workspace", Path(os.environ.get("GITHUB_WORKSPACE") or root))]
    for env_name in ("RUNNER_TEMP", "CARGO_HOME", "CARGO_TARGET_DIR"):
        value = os.environ.get(env_name)
        if value:
            paths.append((env_name.lower(), Path(value)))

    print(f"Disk summary: {label}")
    print("| Label | Path | Total | Used | Free |")
    print("|---|---|---:|---:|---:|")
    for entry in disk_summary_entries(paths):
        print(
            f"| {entry.label} | `{entry.path}` | {format_gib(entry.total_bytes)} | "
            f"{format_gib(entry.used_bytes)} | {format_gib(entry.free_bytes)} |"
        )


def copy_asset(source: Path, destination_dir: Path, name: str) -> None:
    if not source.exists():
        raise FileNotFoundError(f"expected build output does not exist: {source}")
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / name
    shutil.copy2(source, destination)
    print(f"Collected {destination}")


def build_shard(
    root: Path,
    platform: str,
    arch: str,
    bundle_target: str,
    languages: Iterable[str],
    dist_dir: Path,
    distribution_config: Path | None = None,
) -> None:
    config = load_project_config(root)
    zed_root = zed_checkout_path(root, config)
    ensure_inside_workspace(root, zed_root)
    distribution = (
        load_distribution_config(distribution_config) if distribution_config is not None else None
    )
    release_tag = os.environ.get("ZED_I18N_RELEASE_TAG") or os.environ.get("GITHUB_REF_NAME")
    repository = os.environ.get("ZED_I18N_REPOSITORY") or os.environ.get("GITHUB_REPOSITORY")

    for language in languages:
        reset_zed_checkout(zed_root)
        if platform == "windows":
            prepare_windows_bundle_script(zed_root)
        apply_language(root, zed_root, language)
        if distribution is not None:
            apply_distribution_patches(zed_root, distribution)
        patch_remote_server_build(zed_root, platform)
        env = bundle_env(
            zed_root,
            platform,
            distribution=distribution,
            language=language,
            release_tag=release_tag,
            repository=repository,
        )
        run_bundle_command_with_retry(
            platform,
            bundle_target,
            bundle_command(platform, arch, bundle_target),
            zed_root,
            env,
        )
        if platform == "windows":
            create_windows_portable_zip(
                zed_root,
                arch,
                windows_portable_source_path(zed_root, arch, distribution),
            )
        copy_asset(
            app_source_path(zed_root, platform, arch, distribution),
            dist_dir,
            app_asset_name(language, platform, arch),
        )
        if platform == "windows":
            copy_asset(
                windows_portable_source_path(zed_root, arch, distribution),
                dist_dir,
                windows_portable_asset_name(language, arch),
            )

    reset_zed_checkout(zed_root)


APP_PATTERNS = (
    (
        re.compile(r"^zed-i18n-(?P<locale>.+)-linux-(?P<arch>x86_64|aarch64)\.tar\.gz$"),
        "linux",
        "app",
    ),
    (
        re.compile(r"^Zed-i18n-(?P<locale>.+)-macos-(?P<arch>x86_64|aarch64)\.dmg$"),
        "macos",
        "app",
    ),
    (
        re.compile(r"^Zed-i18n-(?P<locale>.+)-windows-(?P<arch>x86_64|aarch64)\.exe$"),
        "windows",
        "app",
    ),
    (
        re.compile(r"^Zed-i18n-(?P<locale>.+)-windows-(?P<arch>x86_64|aarch64)\.zip$"),
        "windows",
        "portable_app",
    ),
)
REMOTE_PATTERN = re.compile(
    r"^zed-remote-server-(?:linux|macos|windows)-(?:x86_64|aarch64)\.(?:gz|zip)$"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_asset(path: Path) -> dict[str, object]:
    name = path.name
    for pattern, platform, kind in APP_PATTERNS:
        match = pattern.match(name)
        if match:
            return {
                "name": name,
                "kind": kind,
                "locale": match.group("locale"),
                "platform": platform,
                "arch": match.group("arch"),
            }

    raise ValueError(f"unrecognized release asset name: {name}")


def is_remote_server_asset(path: Path) -> bool:
    return REMOTE_PATTERN.match(path.name) is not None


def generate_release_metadata(
    root: Path,
    dist_dir: Path,
    manifest_path: Path,
    checksums_path: Path,
    release_tag: str | None,
    repository: str | None,
    run_id: str | None,
    expected_assets: Iterable[str] | None = None,
) -> None:
    config = load_project_config(root)
    excluded = {manifest_path.resolve(), checksums_path.resolve()}
    files = sorted(path for path in dist_dir.iterdir() if path.is_file() and path.resolve() not in excluded)
    assets: list[dict[str, object]] = []
    checksum_lines: list[str] = []
    i18n_revision = int(parse_i18n_revision(release_tag))

    for path in files:
        if is_remote_server_asset(path):
            continue
        checksum = sha256_file(path)
        info = classify_asset(path)
        info["size"] = path.stat().st_size
        info["sha256"] = checksum
        if repository and release_tag:
            info["download_url"] = (
                f"https://github.com/{repository}/releases/download/{release_tag}/{path.name}"
            )
        assets.append(info)
        checksum_lines.append(f"{checksum}  {path.name}")

    if expected_assets is not None:
        expected = set(expected_assets)
        actual = {asset["name"] for asset in assets}
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        if missing or unexpected:
            details = []
            if missing:
                details.append("missing expected release assets: " + ", ".join(missing))
            if unexpected:
                details.append("unexpected release assets: " + ", ".join(unexpected))
            raise ValueError("; ".join(details))

    manifest = {
        "schema": 2,
        "zed_version": config.zed_version,
        "zed_commit": config.zed_commit,
        "i18n_revision": i18n_revision,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "release_tag": release_tag,
        "repository": repository,
        "latest_manifest_url": resolve_update_manifest_url(DistributionConfig(), repository),
        "run_id": run_id,
        "asset_count": len(assets),
        "assets": assets,
    }
    write_json(manifest_path, manifest)
    checksums_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")


def resolve_workspace_path(root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return ensure_inside_workspace(root, path.resolve())


def append_github_file(env_name: str, lines: Iterable[str]) -> None:
    path = os.environ.get(env_name)
    if not path:
        return
    with Path(path).open("a", encoding="utf-8", newline="\n") as file:
        for line in lines:
            file.write(f"{line}\n")


def github_actions_cargo_home(root: Path, platform: str) -> Path:
    if platform == "windows":
        workspace = Path(os.environ.get("GITHUB_WORKSPACE", root))
        anchor = workspace.anchor or workspace.drive
        if not anchor:
            return root / ".cargo-home"
        return Path(anchor) / "c"

    runner_temp = Path(os.environ.get("RUNNER_TEMP", root / ".tmp"))
    return runner_temp / "cargo-home"


def configure_github_rust_cache_env(root: Path, platform: str) -> None:
    cargo_home = github_actions_cargo_home(root, platform)
    cargo_bin = cargo_home / "bin"
    cargo_bin.mkdir(parents=True, exist_ok=True)

    if platform == "windows":
        subprocess.run(["git", "config", "--global", "core.longpaths", "true"], check=False)

    append_github_file(
        "GITHUB_ENV",
        [
            f"CARGO_HOME={cargo_home}",
            "CARGO_NET_GIT_FETCH_WITH_CLI=true",
        ],
    )
    append_github_file("GITHUB_PATH", [str(cargo_bin)])
    cargo_home_for_actions = str(cargo_home).replace("\\", "/")
    append_github_file("GITHUB_OUTPUT", [f"cargo-home={cargo_home_for_actions}"])

    print(f"Using CARGO_HOME={cargo_home}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tools.zed_i18n.ci_release")
    parser.add_argument("--root", default=".", help="zed-i18n repository root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    matrix_parser = subparsers.add_parser("matrix")
    matrix_parser.add_argument("--languages", default="all")
    matrix_parser.add_argument("--platforms", default="all")
    matrix_parser.add_argument("--shard-size", type=int, default=1)

    build_parser = subparsers.add_parser("build-shard")
    build_parser.add_argument("--platform", required=True)
    build_parser.add_argument("--arch", required=True)
    build_parser.add_argument("--bundle-target", default="")
    build_parser.add_argument("--languages", required=True)
    build_parser.add_argument("--dist-dir", required=True)
    build_parser.add_argument(
        "--distribution-config",
        help="Optional distribution patch config. Omit for an upstream-identical Zed build.",
    )

    metadata_parser = subparsers.add_parser("metadata")
    metadata_parser.add_argument("--dist-dir", required=True)
    metadata_parser.add_argument("--manifest", required=True)
    metadata_parser.add_argument("--checksums", required=True)
    metadata_parser.add_argument("--release-tag")
    metadata_parser.add_argument("--repository")
    metadata_parser.add_argument("--run-id")
    metadata_parser.add_argument("--languages")
    metadata_parser.add_argument("--platforms")

    rust_cache_parser = subparsers.add_parser("rust-cache-env")
    rust_cache_parser.add_argument("--platform", required=True, choices=["linux", "macos", "windows"])

    disk_parser = subparsers.add_parser("disk-summary")
    disk_parser.add_argument("--label", default="snapshot")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    try:
        if args.command == "matrix":
            write_github_matrix_outputs(root, args.languages, args.platforms, args.shard_size)
            return 0
        if args.command == "disk-summary":
            print_disk_summary(root, args.label)
            return 0
        if args.command == "build-shard":
            dist_dir = ensure_inside_workspace(root, Path(args.dist_dir).resolve())
            build_shard(
                root=root,
                platform=args.platform,
                arch=args.arch,
                bundle_target=args.bundle_target,
                languages=select_languages(root, args.languages),
                dist_dir=dist_dir,
                distribution_config=(
                    resolve_workspace_path(root, args.distribution_config)
                    if args.distribution_config
                    else None
                ),
            )
            return 0
        if args.command == "metadata":
            expected_assets = None
            if args.languages or args.platforms:
                expected_assets = expected_app_asset_names(
                    select_languages(root, args.languages),
                    select_platforms(args.platforms),
                )
            generate_release_metadata(
                root=root,
                dist_dir=ensure_inside_workspace(root, Path(args.dist_dir).resolve()),
                manifest_path=ensure_inside_workspace(root, Path(args.manifest).resolve()),
                checksums_path=ensure_inside_workspace(root, Path(args.checksums).resolve()),
                release_tag=args.release_tag,
                repository=args.repository,
                run_id=args.run_id,
                expected_assets=expected_assets,
            )
            return 0
        if args.command == "rust-cache-env":
            configure_github_rust_cache_env(root, args.platform)
            return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    parser.error(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
