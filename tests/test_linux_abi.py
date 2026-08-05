import io
import shutil
import subprocess
import tarfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.zed_i18n.linux_abi import (
    parse_glibc_versions,
    verify_archive,
)


class LinuxAbiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path.cwd() / "tests" / ".tmp" / self._testMethodName
        shutil.rmtree(self.root, ignore_errors=True)
        (self.root / "config").mkdir(parents=True)
        (self.root / "config" / "linux-builder.toml").write_text(
            'image_repository = "ghcr.io/li-na/test-builder"\n'
            'tag_prefix = "focal"\n'
            'context_paths = ["config/linux-builder.toml"]\n'
            'required_platforms = ["linux/amd64", "linux/arm64"]\n'
            '\n[glibc_max]\n'
            'x86_64 = "2.31"\n'
            'aarch64 = "2.35"\n',
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def make_archive(self, members: dict[str, bytes]) -> Path:
        archive_path = self.root / "artifact.tar.gz"
        with tarfile.open(archive_path, "w:gz") as archive:
            for name, contents in members.items():
                info = tarfile.TarInfo(name)
                info.size = len(contents)
                info.mode = 0o755
                archive.addfile(info, io.BytesIO(contents))
        return archive_path

    def test_parses_and_orders_glibc_symbol_versions(self) -> None:
        output = """
          0x069691b4 0x00 04 GLIBC_2.34
          0x09691a75 0x00 02 GLIBC_2.2.5
          0x06969197 0x00 03 GLIBC_2.17
          Name: GLIBCXX_3.4.29
          Parent 1: GLIBC_2.34
        """

        self.assertEqual(
            parse_glibc_versions(output),
            {(2, 2, 5), (2, 17), (2, 34)},
        )

    @patch("tools.zed_i18n.linux_abi.subprocess.run")
    def test_accepts_archive_at_architecture_limit(self, run: unittest.mock.Mock) -> None:
        archive = self.make_archive(
            {
                "zed.app/bin/zed": b"\x7fELFbinary",
                "zed.app/share/readme.txt": b"not an ELF",
            }
        )
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="Name: GLIBC_2.31\nName: GLIBC_2.17\n", stderr=""
        )

        report = verify_archive(self.root, archive, "x86_64")

        self.assertEqual(report.elf_count, 1)
        self.assertEqual(report.maximum_required, (2, 31))
        self.assertEqual(report.limit, (2, 31))
        self.assertEqual(report.offenders, ())
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0][:3], ["readelf", "--version-info", "--wide"])

    @patch("tools.zed_i18n.linux_abi.subprocess.run")
    def test_rejects_archive_over_architecture_limit(self, run: unittest.mock.Mock) -> None:
        archive = self.make_archive({"zed.app/libexec/zed-editor": b"\x7fELFbinary"})
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="Name: GLIBC_2.34\n", stderr=""
        )

        with self.assertRaisesRegex(ValueError, r"GLIBC 2\.34.*limit 2\.31.*zed-editor"):
            verify_archive(self.root, archive, "x86_64")

    @patch("tools.zed_i18n.linux_abi.subprocess.run")
    def test_uses_separate_aarch64_limit(self, run: unittest.mock.Mock) -> None:
        archive = self.make_archive({"zed.app/libexec/zed-editor": b"\x7fELFbinary"})
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="Name: GLIBC_2.34\n", stderr=""
        )

        report = verify_archive(self.root, archive, "aarch64")

        self.assertEqual(report.limit, (2, 35))
        self.assertEqual(report.maximum_required, (2, 34))

    def test_rejects_archive_path_traversal_before_extraction(self) -> None:
        archive = self.make_archive({"../escape": b"\x7fELFbinary"})

        with self.assertRaisesRegex(ValueError, "unsafe archive member"):
            verify_archive(self.root, archive, "x86_64")
        self.assertFalse((self.root.parent / "escape").exists())

    def test_rejects_archives_without_elf_files(self) -> None:
        archive = self.make_archive({"zed.app/share/readme.txt": b"plain text"})

        with self.assertRaisesRegex(ValueError, "contains no ELF files"):
            verify_archive(self.root, archive, "x86_64")

    def test_rejects_unknown_architecture(self) -> None:
        archive = self.make_archive({"zed.app/bin/zed": b"\x7fELFbinary"})

        with self.assertRaisesRegex(ValueError, "unsupported Linux architecture"):
            verify_archive(self.root, archive, "riscv64")


if __name__ == "__main__":
    unittest.main()
