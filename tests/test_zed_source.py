import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.zed_i18n.config import ProjectConfig
from tools.zed_i18n.zed_source import (
    build_clone_command,
    ensure_inside_workspace,
    verify_checkout_revision,
)


class ZedSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path.cwd() / "tests" / ".tmp" / self._testMethodName
        shutil.rmtree(self.root, ignore_errors=True)
        self.root.mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_builds_depth_one_fixed_tag_clone_command(self) -> None:
        config = ProjectConfig(
            zed_version="v1.0.0",
            zed_repository="https://github.com/zed-industries/zed",
            cache_dir=Path(".cache/zed"),
        )
        checkout = self.root / ".cache" / "zed" / "v1.0.0"

        command = build_clone_command(config, checkout)

        self.assertEqual(
            command,
            [
                "git",
                "clone",
                "--branch",
                "v1.0.0",
                "--depth",
                "1",
                "https://github.com/zed-industries/zed",
                str(checkout),
            ],
        )

    def test_rejects_paths_outside_workspace(self) -> None:
        outside = self.root.parent / "outside"

        with self.assertRaises(ValueError):
            ensure_inside_workspace(self.root, outside)

    def test_accepts_paths_inside_workspace(self) -> None:
        inside = self.root / ".cache" / "zed" / "v1.0.0"

        self.assertEqual(ensure_inside_workspace(self.root, inside), inside.resolve())

    def test_verifies_checkout_commit_when_configured(self) -> None:
        config = ProjectConfig(
            zed_version="v1.0.0",
            zed_repository="https://github.com/zed-industries/zed",
            cache_dir=Path(".cache/zed"),
            zed_commit="abc123",
        )
        checkout = self.root / ".cache" / "zed" / "v1.0.0"

        with patch("tools.zed_i18n.zed_source.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="abc123\n",
            )

            verify_checkout_revision(config, checkout)

        run.assert_called_once_with(
            ["git", "rev-parse", "HEAD"],
            cwd=checkout,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )

    def test_rejects_checkout_commit_mismatch(self) -> None:
        config = ProjectConfig(
            zed_version="v1.0.0",
            zed_repository="https://github.com/zed-industries/zed",
            cache_dir=Path(".cache/zed"),
            zed_commit="abc123",
        )

        with patch("tools.zed_i18n.zed_source.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="def456\n",
            )

            with self.assertRaisesRegex(ValueError, "expected Zed v1.0.0 at abc123"):
                verify_checkout_revision(config, self.root)


if __name__ == "__main__":
    unittest.main()
