from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
import tarfile
import tempfile
from typing import Sequence

from tools.zed_i18n.linux_builder import load_builder_config


GLIBC_VERSION_RE = re.compile(r"\bGLIBC_(\d+(?:\.\d+)+)\b")


@dataclass(frozen=True)
class AbiReport:
    archive: Path
    architecture: str
    elf_count: int
    maximum_required: tuple[int, ...] | None
    limit: tuple[int, ...]
    offenders: tuple[str, ...]


def parse_glibc_versions(output: str) -> set[tuple[int, ...]]:
    return {
        tuple(int(component) for component in match.group(1).split("."))
        for match in GLIBC_VERSION_RE.finditer(output)
    }


def _version(value: str) -> tuple[int, ...]:
    if not re.fullmatch(r"\d+(?:\.\d+)+", value):
        raise ValueError(f"invalid version: {value}")
    return tuple(int(component) for component in value.split("."))


def _format_version(value: tuple[int, ...] | None) -> str:
    if value is None:
        return "none"
    return ".".join(str(component) for component in value)


def validate_archive_members(members: Sequence[tarfile.TarInfo]) -> None:
    seen: set[str] = set()
    for member in members:
        name = member.name
        path = PurePosixPath(name)
        if (
            not name
            or "\\" in name
            or path.is_absolute()
            or ".." in path.parts
            or name in seen
            or member.ischr()
            or member.isblk()
            or member.isfifo()
        ):
            raise ValueError(f"unsafe archive member: {name}")
        seen.add(name)

        if member.issym() or member.islnk():
            link = member.linkname
            if not link or "\\" in link or PurePosixPath(link).is_absolute():
                raise ValueError(f"unsafe archive member link: {name} -> {link}")
            base = posixpath.dirname(name) if member.issym() else ""
            resolved = PurePosixPath(posixpath.normpath(posixpath.join(base, link)))
            if resolved.is_absolute() or ".." in resolved.parts:
                raise ValueError(f"unsafe archive member link: {name} -> {link}")


def _readelf_versions(path: Path, readelf: str) -> set[tuple[int, ...]]:
    result = subprocess.run(
        [readelf, "--version-info", "--wide", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError(f"readelf failed for {path}: {result.stderr.strip()}")
    return parse_glibc_versions(result.stdout)


def verify_archive(
    root: Path,
    archive_path: Path,
    architecture: str,
    *,
    readelf: str = "readelf",
) -> AbiReport:
    config = load_builder_config(root)
    if architecture not in config.glibc_max:
        raise ValueError(f"unsupported Linux architecture: {architecture}")
    limit = _version(config.glibc_max[architecture])
    archive_path = archive_path.resolve()
    if not archive_path.is_file():
        raise ValueError(f"Linux release archive does not exist: {archive_path}")

    with tempfile.TemporaryDirectory(prefix="zed-i18n-abi-") as temp_dir:
        extract_root = Path(temp_dir)
        with tarfile.open(archive_path, "r:*") as archive:
            members = archive.getmembers()
            validate_archive_members(members)
            archive.extractall(extract_root, members=members, filter="data")

        version_by_file: dict[str, tuple[int, ...]] = {}
        elf_count = 0
        for member in members:
            if not member.isfile():
                continue
            extracted_path = extract_root.joinpath(*PurePosixPath(member.name).parts)
            with extracted_path.open("rb") as handle:
                if handle.read(4) != b"\x7fELF":
                    continue
            elf_count += 1
            versions = _readelf_versions(extracted_path, readelf)
            if versions:
                version_by_file[member.name] = max(versions)

    if elf_count == 0:
        raise ValueError(f"Linux release archive contains no ELF files: {archive_path}")

    maximum_required = max(version_by_file.values(), default=None)
    offenders = tuple(
        f"{name} (GLIBC {_format_version(version)})"
        for name, version in sorted(version_by_file.items())
        if version > limit
    )
    report = AbiReport(
        archive=archive_path,
        architecture=architecture,
        elf_count=elf_count,
        maximum_required=maximum_required,
        limit=limit,
        offenders=offenders,
    )
    if offenders:
        raise ValueError(
            f"artifact requires GLIBC {_format_version(maximum_required)}, above {architecture} "
            f"limit {_format_version(limit)}: {', '.join(offenders)}"
        )
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify GLIBC requirements in Linux release archives.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--arch", required=True)
    parser.add_argument("archives", type=Path, nargs="+")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    for archive in args.archives:
        report = verify_archive(args.root, archive, args.arch)
        print(
            f"ABI verified: {archive} contains {report.elf_count} ELF files, "
            f"maximum GLIBC {_format_version(report.maximum_required)}, "
            f"limit {_format_version(report.limit)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
