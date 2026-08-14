import hashlib
import io
import shutil
import tarfile
import unittest
from pathlib import Path

from tools.zed_i18n.deb import (
    build_deb_from_tarball,
    build_release_debs,
    deb_asset_name,
    deb_package_name,
    deb_version,
    launcher_script,
    rewrite_desktop_entry,
)


FIXTURE_MTIME = 1_700_000_000
FIXTURE_DESKTOP = (
    "[Desktop Entry]\n"
    "Version=1.0\n"
    "Type=Application\n"
    "Name=Zed i18n\n"
    "GenericName=Text Editor\n"
    "TryExec=zed\n"
    "Exec=zed %U\n"
    "Icon=zed\n"
    "Actions=NewWorkspace;\n"
    "\n"
    "[Desktop Action NewWorkspace]\n"
    "Exec=zed --new %U\n"
    "Name=Open a new workspace\n"
)


def read_ar_archive(path: Path) -> tuple[list[str], dict[str, bytes]]:
    data = path.read_bytes()
    if data[:8] != b"!<arch>\n":
        raise AssertionError("not an ar archive")
    order: list[str] = []
    members: dict[str, bytes] = {}
    offset = 8
    while offset < len(data):
        header = data[offset : offset + 60]
        if header[58:60] != b"`\n":
            raise AssertionError("invalid ar member header")
        name = header[:16].decode("ascii").strip()
        size = int(header[48:58].decode("ascii").strip())
        start = offset + 60
        order.append(name)
        members[name] = data[start : start + size]
        offset = start + size + (size % 2)
    return order, members


class DebTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path.cwd() / "tests" / ".tmp" / self._testMethodName
        shutil.rmtree(self.temp_root, ignore_errors=True)
        self.temp_root.mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def add_member(
        self,
        tar: tarfile.TarFile,
        name: str,
        data: bytes = b"",
        mode: int = 0o644,
        typ: bytes = tarfile.REGTYPE,
    ) -> None:
        info = tarfile.TarInfo(name)
        info.mtime = FIXTURE_MTIME
        info.mode = mode
        info.type = typ
        if typ == tarfile.REGTYPE:
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        else:
            tar.addfile(info)

    def make_tarball(self, path: Path, desktop_name: str = "dev.zed-i18n.Zed.desktop") -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(path, "w:gz") as tar:
            self.add_member(tar, "zed.app", mode=0o755, typ=tarfile.DIRTYPE)
            self.add_member(tar, "zed.app/bin", mode=0o755, typ=tarfile.DIRTYPE)
            self.add_member(tar, "zed.app/bin/zed", b"cli-binary", mode=0o755)
            self.add_member(tar, "zed.app/libexec/zed-editor", b"editor-binary", mode=0o755)
            self.add_member(tar, "zed.app/lib/libstdc++.so.6", b"bundled-lib")
            self.add_member(
                tar,
                f"zed.app/share/applications/{desktop_name}",
                FIXTURE_DESKTOP.encode("utf-8"),
                mode=0o755,
            )
            self.add_member(tar, "zed.app/share/icons/hicolor/512x512/apps/zed.png", b"png512")
            self.add_member(
                tar, "zed.app/share/icons/hicolor/1024x1024/apps/zed.png", b"png1024"
            )
            self.add_member(tar, "zed.app/licenses.md", b"bundled licenses")
        return path

    def write_project_configs(self) -> None:
        (self.temp_root / "config").mkdir()
        (self.temp_root / "config" / "project.toml").write_text(
            'zed_version = "v1.2.5"\n'
            'zed_repository = "https://github.com/zed-industries/zed"\n'
            'cache_dir = ".cache/zed"\n',
            encoding="utf-8",
        )
        (self.temp_root / "config" / "linux-builder.toml").write_text(
            'image_repository = "ghcr.io/li-na/zed-i18n-linux-builder"\n'
            'tag_prefix = "focal"\n'
            'context_paths = ["config/linux-builder.toml", "docker/linux-builder"]\n'
            'required_platforms = ["linux/amd64", "linux/arm64"]\n'
            "[glibc_max]\n"
            'x86_64 = "2.31"\n'
            'aarch64 = "2.31"\n',
            encoding="utf-8",
        )

    def test_deb_asset_name_keeps_release_asset_convention(self) -> None:
        self.assertEqual(
            deb_asset_name("ko-KR", "x86_64"),
            "zed-i18n-ko-KR-linux-x86_64.deb",
        )
        self.assertEqual(deb_asset_name(None, "aarch64"), "zed-i18n-linux-aarch64.deb")

    def test_deb_package_name_lowercases_locale(self) -> None:
        self.assertEqual(deb_package_name("ko-KR"), "zed-i18n-ko-kr")
        self.assertEqual(deb_package_name(None), "zed-i18n")
        with self.assertRaises(ValueError):
            deb_package_name("ko KR")

    def test_deb_version_maps_release_tag_and_falls_back(self) -> None:
        self.assertEqual(deb_version("v1.2.5-i18n.4", "v1.2.5"), "1.2.5+i18n.4")
        self.assertEqual(deb_version(None, "v1.2.5"), "1.2.5+i18n.0")
        self.assertEqual(deb_version("master", "v1.2.5"), "1.2.5+i18n.0")
        with self.assertRaises(ValueError):
            deb_version("master", "vNext")

    def test_rewrite_desktop_entry_targets_packaged_launcher(self) -> None:
        rewritten = rewrite_desktop_entry(FIXTURE_DESKTOP, "zed-i18n", "zed-i18n")

        self.assertIn("TryExec=zed-i18n\n", rewritten)
        self.assertIn("Exec=zed-i18n %U\n", rewritten)
        self.assertIn("Exec=zed-i18n --new %U\n", rewritten)
        self.assertIn("Icon=zed-i18n\n", rewritten)
        self.assertNotIn("Exec=zed %U", rewritten)

    def test_rewrite_desktop_entry_requires_exec_line(self) -> None:
        with self.assertRaisesRegex(ValueError, "no Exec line"):
            rewrite_desktop_entry("[Desktop Entry]\nName=Zed\n", "zed-i18n", "zed-i18n")

    def test_build_deb_creates_debian_package(self) -> None:
        tarball = self.make_tarball(self.temp_root / "zed-i18n-ko-KR-linux-x86_64.tar.gz")
        output = self.temp_root / "zed-i18n-ko-KR-linux-x86_64.deb"

        build_deb_from_tarball(
            tarball,
            output,
            locale="ko-KR",
            arch="x86_64",
            version="1.2.5+i18n.4",
            repository="owner/repo",
            glibc_floor="2.31",
        )

        order, members = read_ar_archive(output)
        self.assertEqual(order, ["debian-binary", "control.tar.gz", "data.tar.xz"])
        self.assertEqual(members["debian-binary"], b"2.0\n")

        with tarfile.open(fileobj=io.BytesIO(members["control.tar.gz"]), mode="r:gz") as tar:
            control = tar.extractfile("./control").read().decode("utf-8")
            md5sums = tar.extractfile("./md5sums").read().decode("utf-8")

        self.assertIn("Package: zed-i18n-ko-kr\n", control)
        self.assertIn("Version: 1.2.5+i18n.4\n", control)
        self.assertIn("Architecture: amd64\n", control)
        self.assertIn(
            "Depends: libc6 (>= 2.31), libgcc-s1, libasound2 | libasound2t64, libvulkan1\n",
            control,
        )
        self.assertNotIn("Recommends:", control)
        self.assertIn("Provides: zed-i18n\n", control)
        self.assertIn("Conflicts: zed-i18n\n", control)
        self.assertIn("Homepage: https://github.com/owner/repo\n", control)
        self.assertIn("Description: Localized build of the Zed editor (ko-KR)\n", control)

        editor_md5 = hashlib.md5(b"editor-binary").hexdigest()
        self.assertIn(f"{editor_md5}  usr/lib/zed-i18n/libexec/zed-editor\n", md5sums)
        self.assertNotIn("./usr", md5sums)

        with tarfile.open(fileobj=io.BytesIO(members["data.tar.xz"]), mode="r:xz") as tar:
            names = tar.getnames()
            launcher_info = tar.getmember("./usr/bin/zed-i18n")
            launcher = tar.extractfile(launcher_info).read().decode("utf-8")
            desktop_info = tar.getmember("./usr/share/applications/dev.zed-i18n.Zed.desktop")
            desktop = tar.extractfile(desktop_info).read().decode("utf-8")
            editor_info = tar.getmember("./usr/lib/zed-i18n/libexec/zed-editor")
            bundled_lib_info = tar.getmember("./usr/lib/zed-i18n/lib/libstdc++.so.6")
            icon = tar.extractfile("./usr/share/icons/hicolor/512x512/apps/zed-i18n.png").read()

        self.assertIn("./usr", names)
        self.assertLess(names.index("./usr"), names.index("./usr/bin/zed-i18n"))
        self.assertIn("./usr/lib/zed-i18n/bin/zed", names)
        self.assertIn("./usr/lib/zed-i18n/licenses.md", names)
        self.assertIn("./usr/share/doc/zed-i18n-ko-kr/copyright", names)
        self.assertIn("./usr/share/icons/hicolor/1024x1024/apps/zed-i18n.png", names)

        self.assertEqual(launcher_info.mode, 0o755)
        self.assertEqual((launcher_info.uid, launcher_info.gid), (0, 0))
        self.assertEqual((launcher_info.uname, launcher_info.gname), ("root", "root"))
        self.assertTrue(launcher.startswith("#!/bin/sh\n"))
        self.assertIn("ZED_UPDATE_EXPLANATION", launcher)
        self.assertIn("https://github.com/owner/repo/releases/latest", launcher)
        self.assertIn("--uninstall)\n", launcher)
        self.assertIn("sudo apt remove zed-i18n-ko-kr", launcher)
        self.assertLess(launcher.index("--uninstall"), launcher.index("exec /usr/lib/zed-i18n/bin/zed"))
        self.assertIn('exec /usr/lib/zed-i18n/bin/zed "$@"\n', launcher)

        self.assertEqual(desktop_info.mode, 0o644)
        self.assertIn("Exec=zed-i18n %U\n", desktop)
        self.assertIn("Exec=zed-i18n --new %U\n", desktop)
        self.assertIn("TryExec=zed-i18n\n", desktop)
        self.assertIn("Icon=zed-i18n\n", desktop)

        self.assertEqual(editor_info.mode, 0o755)
        self.assertEqual(bundled_lib_info.mode, 0o644)
        self.assertEqual(icon, b"png512")

    def test_build_universal_deb_takes_over_the_virtual_package_name(self) -> None:
        tarball = self.make_tarball(self.temp_root / "zed-i18n-linux-x86_64.tar.gz")
        output = self.temp_root / "zed-i18n-linux-x86_64.deb"

        build_deb_from_tarball(
            tarball,
            output,
            locale=None,
            arch="x86_64",
            version="1.2.5+i18n.4",
            repository="owner/repo",
            glibc_floor="2.31",
        )

        _, members = read_ar_archive(output)
        with tarfile.open(fileobj=io.BytesIO(members["control.tar.gz"]), mode="r:gz") as tar:
            control = tar.extractfile("./control").read().decode("utf-8")

        self.assertIn("Package: zed-i18n\n", control)
        # The real package name is zed-i18n now, so it must not provide itself;
        # Conflicts/Replaces still take over the per-locale providers.
        self.assertNotIn("Provides:", control)
        self.assertIn("Conflicts: zed-i18n\n", control)
        self.assertIn("Replaces: zed-i18n\n", control)
        self.assertIn("Description: Localized build of the Zed editor\n", control)
        self.assertIn("every supported display", control)
        self.assertIn("per-locale", control)

        with tarfile.open(fileobj=io.BytesIO(members["data.tar.xz"]), mode="r:xz") as tar:
            names = tar.getnames()
            launcher = tar.extractfile("./usr/bin/zed-i18n").read().decode("utf-8")

        self.assertIn("./usr/share/doc/zed-i18n/copyright", names)
        self.assertIn('sudo apt remove zed-i18n" >&2', launcher)

    def test_build_deb_fixes_system_desktop_name_for_unpatched_bundles(self) -> None:
        tarball = self.make_tarball(
            self.temp_root / "zed-i18n-ko-KR-linux-x86_64.tar.gz",
            desktop_name="dev.zed.Zed.desktop",
        )
        output = self.temp_root / "zed-i18n-ko-KR-linux-x86_64.deb"

        build_deb_from_tarball(
            tarball,
            output,
            locale="ko-KR",
            arch="x86_64",
            version="1.2.5+i18n.4",
            repository="owner/repo",
            glibc_floor="2.31",
        )

        _, members = read_ar_archive(output)
        with tarfile.open(fileobj=io.BytesIO(members["data.tar.xz"]), mode="r:xz") as tar:
            names = tar.getnames()

        self.assertIn("./usr/share/applications/dev.zed-i18n.Zed.desktop", names)
        self.assertNotIn("./usr/share/applications/dev.zed.Zed.desktop", names)
        # The untouched in-app copy keeps its original name; desktop
        # environments do not scan /usr/lib for entries.
        self.assertIn("./usr/lib/zed-i18n/share/applications/dev.zed.Zed.desktop", names)

    def test_launcher_script_blocks_upstream_uninstall(self) -> None:
        script = launcher_script("owner/repo", "zed-i18n-ja-jp")

        self.assertIn("--uninstall)\n", script)
        self.assertIn("sudo apt remove zed-i18n-ja-jp", script)
        self.assertIn("exit 1\n", script)
        self.assertLess(script.index("exit 1"), script.index("exec /usr/lib/zed-i18n/bin/zed"))
        # "--" ends option parsing, so a file literally named --uninstall stays
        # openable; the guard must stop scanning there.
        self.assertLess(script.index("--)"), script.index("--uninstall)"))

    def test_build_deb_rejects_unsafe_archive(self) -> None:
        tarball = self.temp_root / "zed-i18n-ko-KR-linux-x86_64.tar.gz"
        with tarfile.open(tarball, "w:gz") as tar:
            self.add_member(tar, "zed.app/bin/zed", b"cli", mode=0o755)
            self.add_member(tar, "../evil", b"payload")

        with self.assertRaisesRegex(ValueError, "unsafe archive member"):
            build_deb_from_tarball(
                tarball,
                self.temp_root / "out.deb",
                locale="ko-KR",
                arch="x86_64",
                version="1.2.5+i18n.4",
                repository="owner/repo",
                glibc_floor="2.31",
            )

    def test_build_release_debs_scans_dist_and_maps_architectures(self) -> None:
        self.write_project_configs()
        dist_dir = self.temp_root / "dist"
        self.make_tarball(dist_dir / "zed-i18n-ko-KR-linux-x86_64.tar.gz")
        self.make_tarball(dist_dir / "zed-i18n-ja-JP-linux-aarch64.tar.gz")
        (dist_dir / "zed-remote-server-linux-x86_64.gz").write_bytes(b"server")
        (dist_dir / "Zed-i18n-ko-KR-macos-x86_64.dmg").write_bytes(b"dmg")

        debs = build_release_debs(
            self.temp_root,
            dist_dir,
            release_tag="v1.2.5-i18n.4",
            repository="owner/repo",
            max_workers=1,
        )

        self.assertEqual(
            sorted(path.name for path in debs),
            [
                "zed-i18n-ja-JP-linux-aarch64.deb",
                "zed-i18n-ko-KR-linux-x86_64.deb",
            ],
        )
        _, members = read_ar_archive(dist_dir / "zed-i18n-ja-JP-linux-aarch64.deb")
        with tarfile.open(fileobj=io.BytesIO(members["control.tar.gz"]), mode="r:gz") as tar:
            control = tar.extractfile("./control").read().decode("utf-8")
        self.assertIn("Package: zed-i18n-ja-jp\n", control)
        self.assertIn("Version: 1.2.5+i18n.4\n", control)
        self.assertIn("Architecture: arm64\n", control)

    def test_build_release_debs_packages_universal_tarballs(self) -> None:
        self.write_project_configs()
        dist_dir = self.temp_root / "dist"
        self.make_tarball(dist_dir / "zed-i18n-linux-x86_64.tar.gz")
        self.make_tarball(dist_dir / "zed-i18n-linux-aarch64.tar.gz")

        debs = build_release_debs(
            self.temp_root,
            dist_dir,
            release_tag="v1.2.5-i18n.4",
            repository="owner/repo",
            max_workers=1,
        )

        self.assertEqual(
            sorted(path.name for path in debs),
            ["zed-i18n-linux-aarch64.deb", "zed-i18n-linux-x86_64.deb"],
        )
        _, members = read_ar_archive(dist_dir / "zed-i18n-linux-x86_64.deb")
        with tarfile.open(fileobj=io.BytesIO(members["control.tar.gz"]), mode="r:gz") as tar:
            control = tar.extractfile("./control").read().decode("utf-8")
        self.assertIn("Package: zed-i18n\n", control)
        self.assertIn("Architecture: amd64\n", control)

    def test_build_release_debs_returns_empty_without_linux_archives(self) -> None:
        self.write_project_configs()
        dist_dir = self.temp_root / "dist"
        dist_dir.mkdir()
        (dist_dir / "Zed-i18n-ko-KR-macos-x86_64.dmg").write_bytes(b"dmg")

        self.assertEqual(
            build_release_debs(
                self.temp_root,
                dist_dir,
                release_tag="v1.2.5-i18n.4",
                repository="owner/repo",
            ),
            [],
        )

    def test_release_workflow_builds_debs_before_metadata(self) -> None:
        workflow = (Path.cwd() / ".github" / "workflows" / "i18n-release.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("ci_release build-debs", workflow)
        self.assertIn('dpkg-deb --info "$deb"', workflow)
        self.assertIn('dpkg-deb --contents "$deb"', workflow)
        self.assertLess(
            workflow.index("ci_release build-debs"),
            workflow.index("ci_release metadata"),
        )


if __name__ == "__main__":
    unittest.main()
