"""Repackage localized Linux release tarballs into Debian packages.

The release tarballs are produced by the pinned Ubuntu 20.04 builder, so a
single .deb per locale and architecture covers every distribution at or above
the builder's glibc floor (Debian 11, Ubuntu 20.04). Packages are assembled
with pure Python (ar + control.tar.gz + data.tar.xz) so no dpkg tooling is
required at build time and the output stays deterministic for a given input.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import re
import shutil
import tarfile
import tempfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Iterable

from .config import load_project_config
from .linux_abi import validate_archive_members
from .linux_builder import load_builder_config
from .packaging import RELEASE_TAG_PATTERN


DEFAULT_REPOSITORY = "LI-NA/zed-i18n"
MAINTAINER = "LI-NA <LI-NA@users.noreply.github.com>"
INSTALL_ROOT = "usr/lib/zed-i18n"
CLI_NAME = "zed-i18n"
ICON_NAME = "zed-i18n"
VIRTUAL_PACKAGE = "zed-i18n"
# Fixed regardless of the bundle's APP_ID so an unpatched (distribution_patches
# disabled) build can never install /usr/share/applications/dev.zed.Zed.desktop
# and collide with the official Zed desktop ID.
DESKTOP_FILE_NAME = "dev.zed-i18n.Zed.desktop"

DEB_ARCHITECTURES = {"x86_64": "amd64", "aarch64": "arm64"}
LINUX_TARBALL_PATTERN = re.compile(
    r"^zed-i18n-(?P<locale>.+)-linux-(?P<arch>x86_64|aarch64)\.tar\.gz$"
)
PACKAGE_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9+.-]+$")
ZED_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
ICON_SOURCE_PATTERN = re.compile(
    r"^share/icons/hicolor/(?P<size>\d+x\d+)/apps/[^/]+\.png$"
)
DESKTOP_SOURCE_PATTERN = re.compile(r"^share/applications/[^/]+\.desktop$")


def deb_asset_name(language: str, arch: str) -> str:
    return f"zed-i18n-{language}-linux-{arch}.deb"


def deb_package_name(locale: str) -> str:
    name = f"zed-i18n-{locale.lower()}"
    if not PACKAGE_NAME_PATTERN.fullmatch(name):
        raise ValueError(f"locale does not form a valid Debian package name: {locale}")
    return name


def deb_version(release_tag: str | None, zed_version: str) -> str:
    """Map a release tag to a Debian version.

    The tag's hyphen cannot be reused verbatim because a hyphen separates the
    Debian revision, so `v1.2.5-i18n.4` becomes `1.2.5+i18n.4`. Builds without
    a release tag (manual workflow runs on a branch) fall back to the project's
    Zed version with revision 0.
    """
    if release_tag:
        match = RELEASE_TAG_PATTERN.match(release_tag)
        if match:
            return f"{match.group('base')}+i18n.{int(match.group('revision'))}"
    base = zed_version.removeprefix("v")
    if not ZED_VERSION_PATTERN.fullmatch(base):
        raise ValueError(f"cannot derive a Debian version from: {release_tag or zed_version}")
    return f"{base}+i18n.0"


def rewrite_desktop_entry(content: str, cli_name: str, icon_name: str) -> str:
    """Point the bundled desktop entry at the packaged launcher and icon."""
    lines = []
    exec_lines = 0
    for line in content.splitlines():
        exec_match = re.fullmatch(r"(Exec=)\S+(.*)", line)
        if exec_match:
            exec_lines += 1
            lines.append(f"{exec_match.group(1)}{cli_name}{exec_match.group(2)}")
            continue
        if line.startswith("TryExec="):
            lines.append(f"TryExec={cli_name}")
            continue
        if line.startswith("Icon="):
            lines.append(f"Icon={icon_name}")
            continue
        lines.append(line)
    if exec_lines == 0:
        raise ValueError("desktop entry has no Exec line")
    return "\n".join(lines) + "\n"


def launcher_script(repository: str, package: str) -> str:
    return (
        "#!/bin/sh\n"
        "# Launcher installed by the zed-i18n Debian package.\n"
        "\n"
        "# The upstream CLI bundles zed.dev's install.sh uninstaller. From a dpkg\n"
        "# install it would delete an official install.sh installation and the\n"
        "# shared stable database instead of this package, so block it here.\n"
        '# Arguments after "--" are paths, not options, and stay untouched.\n'
        'for arg in "$@"; do\n'
        '    case "$arg" in\n'
        "        --)\n"
        "            break\n"
        "            ;;\n"
        "        --uninstall)\n"
        '            echo "This Zed i18n build was installed as a Debian package." >&2\n'
        f'            echo "Remove it with: sudo apt remove {package}" >&2\n'
        "            exit 1\n"
        "            ;;\n"
        "    esac\n"
        "done\n"
        "\n"
        "# The install prefix is not user-writable, so disable in-app updates\n"
        "# unless the caller already provided its own explanation.\n"
        'if [ -z "${ZED_UPDATE_EXPLANATION:-}" ]; then\n'
        '    ZED_UPDATE_EXPLANATION="Zed i18n was installed as a Debian package. '
        f"Download the latest package from https://github.com/{repository}/releases/latest "
        'to update."\n'
        "    export ZED_UPDATE_EXPLANATION\n"
        "fi\n"
        f'exec /{INSTALL_ROOT}/bin/zed "$@"\n'
    )


def copyright_file(repository: str) -> str:
    return (
        "Zed i18n is a localized build of the Zed editor.\n"
        "\n"
        f"Packaged from: https://github.com/{repository}\n"
        "Upstream source: https://github.com/zed-industries/zed\n"
        "\n"
        "Zed is licensed under the GNU General Public License version 3 or later\n"
        "(GPL-3.0-or-later). See /usr/share/common-licenses/GPL-3 for the license\n"
        f"text and /{INSTALL_ROOT}/licenses.md for the licenses of bundled\n"
        "third-party components.\n"
    )


def control_file(
    *,
    package: str,
    version: str,
    deb_arch: str,
    installed_size_kib: int,
    locale: str,
    repository: str,
    glibc_floor: str,
) -> str:
    return (
        f"Package: {package}\n"
        f"Version: {version}\n"
        f"Architecture: {deb_arch}\n"
        f"Maintainer: {MAINTAINER}\n"
        f"Installed-Size: {installed_size_kib}\n"
        # libvulkan1 is loaded at runtime by the GPUI renderer; without it Zed
        # cannot open a window, so it is a hard dependency per Debian Policy.
        f"Depends: libc6 (>= {glibc_floor}), libgcc-s1, libasound2 | libasound2t64, libvulkan1\n"
        f"Provides: {VIRTUAL_PACKAGE}\n"
        f"Conflicts: {VIRTUAL_PACKAGE}\n"
        f"Replaces: {VIRTUAL_PACKAGE}\n"
        "Section: editors\n"
        "Priority: optional\n"
        f"Homepage: https://github.com/{repository}\n"
        f"Description: Localized build of the Zed editor ({locale})\n"
        " Zed is a high-performance, multiplayer code editor. This package\n"
        f" installs the community zed-i18n build localized for {locale}.\n"
        " .\n"
        " All locale packages provide the same zed-i18n name, so installing\n"
        " another locale replaces this one.\n"
    )


@dataclass(frozen=True)
class _GeneratedFile:
    name: str
    data: bytes
    mode: int


class _Md5Reader:
    def __init__(self, stream: BinaryIO) -> None:
        self._stream = stream
        self.digest = hashlib.md5()

    def read(self, size: int = -1) -> bytes:
        chunk = self._stream.read(size)
        if chunk:
            self.digest.update(chunk)
        return chunk


def _tar_entry(name: str, *, mode: int, mtime: int, typ: bytes = tarfile.REGTYPE) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.mode = mode
    info.mtime = mtime
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.type = typ
    return info


def _normalized_file_mode(mode: int) -> int:
    return 0o755 if mode & 0o111 else 0o644


def _app_root(members: Iterable[tarfile.TarInfo]) -> str:
    roots = {PurePosixPath(member.name).parts[0] for member in members}
    if len(roots) != 1:
        raise ValueError(f"expected a single top-level directory, found: {sorted(roots)}")
    root = roots.pop()
    if not root.endswith(".app"):
        raise ValueError(f"unexpected top-level directory in Linux archive: {root}")
    return root


def _read_member(archive: tarfile.TarFile, member: tarfile.TarInfo) -> bytes:
    stream = archive.extractfile(member)
    if stream is None:
        raise ValueError(f"cannot read archive member: {member.name}")
    with stream:
        return stream.read()


def _ar_member_bytes(name: str, size: int, mtime: int) -> bytes:
    if len(name) > 16:
        raise ValueError(f"ar member name too long: {name}")
    header = f"{name:<16}{mtime:<12d}{0:<6d}{0:<6d}{'100644':<8}{size:<10d}`\n"
    return header.encode("ascii")


def _write_ar_archive(
    output: BinaryIO,
    control_tar: bytes,
    data_tar_path: Path,
    mtime: int,
) -> None:
    output.write(b"!<arch>\n")

    debian_binary = b"2.0\n"
    output.write(_ar_member_bytes("debian-binary", len(debian_binary), mtime))
    output.write(debian_binary)

    output.write(_ar_member_bytes("control.tar.gz", len(control_tar), mtime))
    output.write(control_tar)
    if len(control_tar) % 2:
        output.write(b"\n")

    data_size = data_tar_path.stat().st_size
    output.write(_ar_member_bytes("data.tar.xz", data_size, mtime))
    with data_tar_path.open("rb") as data_file:
        shutil.copyfileobj(data_file, output)
    if data_size % 2:
        output.write(b"\n")


def _build_control_tar(control: str, md5sums: str, mtime: int) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.GNU_FORMAT) as tar:
        tar.addfile(_tar_entry("./", mode=0o755, mtime=mtime, typ=tarfile.DIRTYPE))
        for name, text in (("./control", control), ("./md5sums", md5sums)):
            data = text.encode("utf-8")
            info = _tar_entry(name, mode=0o644, mtime=mtime)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return gzip.compress(buffer.getvalue(), 9, mtime=0)


def build_deb_from_tarball(
    tarball_path: Path,
    output_path: Path,
    *,
    locale: str,
    arch: str,
    version: str,
    repository: str,
    glibc_floor: str,
) -> Path:
    if arch not in DEB_ARCHITECTURES:
        raise ValueError(f"unsupported Linux architecture: {arch}")
    package = deb_package_name(locale)
    install_prefix = f"./{INSTALL_ROOT}"

    with tarfile.open(tarball_path, "r:gz") as archive:
        members = archive.getmembers()
        validate_archive_members(members)
        app_root = _app_root(members)
        mtime = max((member.mtime for member in members), default=0)

        def remap(name: str) -> str:
            relative = PurePosixPath(name).relative_to(app_root)
            return f"{install_prefix}/{relative}"

        desktop_sources = []
        icon_sources = []
        payload_members = []
        for member in members:
            relative = str(PurePosixPath(member.name).relative_to(app_root)) if member.name != app_root else ""
            if member.isfile() and DESKTOP_SOURCE_PATTERN.fullmatch(relative):
                desktop_sources.append(member)
            icon_match = ICON_SOURCE_PATTERN.fullmatch(relative) if member.isfile() else None
            if icon_match:
                icon_sources.append((icon_match.group("size"), member))
            if not member.isdir():
                payload_members.append(member)

        if len(desktop_sources) != 1:
            names = [member.name for member in desktop_sources]
            raise ValueError(f"expected exactly one desktop entry in archive, found: {names}")
        if not icon_sources:
            raise ValueError("Linux archive contains no application icons")

        desktop_member = desktop_sources[0]
        desktop_text = rewrite_desktop_entry(
            _read_member(archive, desktop_member).decode("utf-8"),
            CLI_NAME,
            ICON_NAME,
        )

        generated = [
            _GeneratedFile(
                f"./usr/bin/{CLI_NAME}",
                launcher_script(repository, package).encode("utf-8"),
                0o755,
            ),
            _GeneratedFile(
                f"./usr/share/applications/{DESKTOP_FILE_NAME}",
                desktop_text.encode("utf-8"),
                0o644,
            ),
            _GeneratedFile(
                f"./usr/share/doc/{package}/copyright",
                copyright_file(repository).encode("utf-8"),
                0o644,
            ),
        ]
        for size, member in icon_sources:
            generated.append(
                _GeneratedFile(
                    f"./usr/share/icons/hicolor/{size}/apps/{ICON_NAME}.png",
                    _read_member(archive, member),
                    0o644,
                )
            )

        file_names = [remap(member.name) for member in payload_members]
        file_names.extend(entry.name for entry in generated)
        counts = Counter(file_names)
        duplicates = sorted(name for name, count in counts.items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate package paths: {duplicates}")

        directories: set[str] = {"./"}
        for name in file_names:
            parent = PurePosixPath(name.removeprefix("./")).parent
            while str(parent) != ".":
                directories.add(f"./{parent}/")
                parent = parent.parent

        md5_lines: list[str] = []
        installed_bytes = 0

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="zed-i18n-deb-", dir=output_path.parent) as temp_dir:
            data_tar_path = Path(temp_dir) / "data.tar.xz"
            with tarfile.open(
                data_tar_path, "w:xz", format=tarfile.GNU_FORMAT, preset=6
            ) as data_tar:
                for name in sorted(directories):
                    data_tar.addfile(
                        _tar_entry(name, mode=0o755, mtime=mtime, typ=tarfile.DIRTYPE)
                    )

                entries: list[tuple[str, tarfile.TarInfo | None, _GeneratedFile | None]] = [
                    (remap(member.name), member, None) for member in payload_members
                ]
                entries.extend((entry.name, None, entry) for entry in generated)
                for name, member, generated_file in sorted(entries, key=lambda item: item[0]):
                    if member is not None and (member.issym() or member.islnk()):
                        typ = tarfile.SYMTYPE if member.issym() else tarfile.LNKTYPE
                        info = _tar_entry(name, mode=0o777, mtime=member.mtime, typ=typ)
                        if member.issym():
                            info.linkname = member.linkname
                        else:
                            info.linkname = remap(member.linkname)
                        data_tar.addfile(info)
                        continue

                    if member is not None:
                        info = _tar_entry(
                            name,
                            mode=_normalized_file_mode(member.mode),
                            mtime=member.mtime,
                        )
                        info.size = member.size
                        source = archive.extractfile(member)
                        if source is None:
                            raise ValueError(f"cannot read archive member: {member.name}")
                        with source:
                            reader = _Md5Reader(source)
                            data_tar.addfile(info, reader)
                        digest = reader.digest
                        size = member.size
                    else:
                        assert generated_file is not None
                        info = _tar_entry(name, mode=generated_file.mode, mtime=mtime)
                        info.size = len(generated_file.data)
                        data_tar.addfile(info, io.BytesIO(generated_file.data))
                        digest = hashlib.md5(generated_file.data)
                        size = len(generated_file.data)

                    md5_lines.append(f"{digest.hexdigest()}  {name.removeprefix('./')}")
                    installed_bytes += size

            control = control_file(
                package=package,
                version=version,
                deb_arch=DEB_ARCHITECTURES[arch],
                installed_size_kib=(installed_bytes + 1023) // 1024,
                locale=locale,
                repository=repository,
                glibc_floor=glibc_floor,
            )
            control_tar = _build_control_tar(control, "\n".join(md5_lines) + "\n", mtime)

            partial_path = Path(temp_dir) / "package.deb"
            with partial_path.open("wb") as output:
                _write_ar_archive(output, control_tar, data_tar_path, mtime)
            partial_path.replace(output_path)

    return output_path


def _build_one(job: tuple[str, str, str, str, str, str, str]) -> str:
    tarball, output, locale, arch, version, repository, glibc_floor = job
    build_deb_from_tarball(
        Path(tarball),
        Path(output),
        locale=locale,
        arch=arch,
        version=version,
        repository=repository,
        glibc_floor=glibc_floor,
    )
    return output


def find_linux_tarballs(dist_dir: Path) -> list[tuple[Path, str, str]]:
    tarballs = []
    for path in sorted(dist_dir.iterdir()):
        if not path.is_file():
            continue
        match = LINUX_TARBALL_PATTERN.match(path.name)
        if match:
            tarballs.append((path, match.group("locale"), match.group("arch")))
    return tarballs


def build_release_debs(
    root: Path,
    dist_dir: Path,
    release_tag: str | None,
    repository: str | None,
    *,
    max_workers: int | None = None,
) -> list[Path]:
    project = load_project_config(root)
    builder = load_builder_config(root)
    version = deb_version(release_tag, project.zed_version)
    repository = repository or DEFAULT_REPOSITORY

    jobs = []
    for tarball, locale, arch in find_linux_tarballs(dist_dir):
        output = dist_dir / deb_asset_name(locale, arch)
        jobs.append(
            (
                str(tarball),
                str(output),
                locale,
                arch,
                version,
                repository,
                builder.glibc_max[arch],
            )
        )

    if not jobs:
        return []
    if len(jobs) == 1 or (max_workers is not None and max_workers <= 1):
        return [Path(_build_one(job)) for job in jobs]

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        return [Path(output) for output in executor.map(_build_one, jobs)]
