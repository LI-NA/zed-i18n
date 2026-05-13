import shutil
import unittest
from pathlib import Path

from tools.zed_i18n.config import load_project_config, zed_checkout_path


class ProjectConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path.cwd() / "tests" / ".tmp" / self._testMethodName
        shutil.rmtree(self.temp_root, ignore_errors=True)
        self.temp_root.mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_loads_project_config_from_toml(self) -> None:
        root = self.temp_root
        config_dir = root / "config"
        config_dir.mkdir()
        (config_dir / "project.toml").write_text(
            '\n'.join(
                [
                    'zed_version = "v1.0.0"',
                    'zed_commit = "abc123"',
                    'zed_repository = "https://github.com/zed-industries/zed"',
                    'cache_dir = ".cache/zed"',
                ]
            ),
            encoding="utf-8",
        )

        config = load_project_config(root)

        self.assertEqual(config.zed_version, "v1.0.0")
        self.assertEqual(config.zed_commit, "abc123")
        self.assertEqual(config.zed_repository, "https://github.com/zed-industries/zed")
        self.assertEqual(config.cache_dir, Path(".cache/zed"))

    def test_resolves_versioned_zed_checkout_path(self) -> None:
        root = self.temp_root
        config_dir = root / "config"
        config_dir.mkdir()
        (config_dir / "project.toml").write_text(
            'zed_version = "v1.0.0"\n'
            'zed_repository = "https://github.com/zed-industries/zed"\n'
            'cache_dir = ".cache/zed"\n',
            encoding="utf-8",
        )
        config = load_project_config(root)

        self.assertEqual(
            zed_checkout_path(root, config),
            root / ".cache" / "zed" / "v1.0.0",
        )


if __name__ == "__main__":
    unittest.main()
