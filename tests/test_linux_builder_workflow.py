import re
import unittest
from pathlib import Path


class LinuxBuilderWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow_path = Path.cwd() / ".github" / "workflows" / "i18n-linux-builder.yml"
        cls.workflow = cls.workflow_path.read_text(encoding="utf-8")

    def test_publishes_to_ghcr_with_narrow_permissions_and_concurrency(self) -> None:
        self.assertIn("packages: write", self.workflow)
        self.assertIn("contents: read", self.workflow)
        self.assertIn("ghcr.io", self.workflow)
        self.assertIn("docker login ghcr.io", self.workflow)
        self.assertIn("concurrency:", self.workflow)
        self.assertIn("i18n-linux-builder-${{ github.ref }}", self.workflow)
        self.assertIn("cancel-in-progress: false", self.workflow)

    def test_builds_each_platform_on_its_native_free_runner(self) -> None:
        self.assertIn("ubuntu-24.04", self.workflow)
        self.assertIn("ubuntu-24.04-arm", self.workflow)
        self.assertIn("platform: linux/amd64", self.workflow)
        self.assertIn("platform: linux/arm64", self.workflow)
        self.assertIn("arch: x86_64", self.workflow)
        self.assertIn("arch: aarch64", self.workflow)
        self.assertNotIn("setup-qemu", self.workflow)

    def test_uses_content_tag_and_all_pinned_build_arguments(self) -> None:
        self.assertIn("tools.zed_i18n.linux_builder outputs", self.workflow)
        self.assertIn("--build-arg UBUNTU_BASE=", self.workflow)
        self.assertIn("--build-arg RUST_TOOLCHAIN=", self.workflow)
        self.assertIn("--build-arg RUST_PROFILE=", self.workflow)
        self.assertIn("--build-arg RUST_COMPONENTS=", self.workflow)
        self.assertIn("--build-arg RUST_TARGETS=", self.workflow)
        self.assertIn("--build-arg WASI_SDK_VERSION=", self.workflow)
        self.assertIn("--build-arg UV_VERSION=", self.workflow)
        self.assertIn("--build-arg PYTHON_VERSION=", self.workflow)
        self.assertIn("--build-arg BUILD_CONTEXT_SHA256=", self.workflow)
        self.assertIn("--provenance=false", self.workflow)
        self.assertIn("--sbom=false", self.workflow)

    def test_reuses_valid_manifest_and_assembles_from_immutable_children(self) -> None:
        self.assertIn("docker buildx imagetools inspect", self.workflow)
        self.assertIn("--format '{{.Name}}'", self.workflow)
        self.assertIn("--format '{{json .Manifest}}'", self.workflow)
        self.assertIn("resolve-manifest", self.workflow)
        self.assertIn("docker buildx imagetools create", self.workflow)
        self.assertIn('sources+=("${resolved}")', self.workflow)
        self.assertIn("should-build", self.workflow)

    def test_relevant_builder_inputs_trigger_publication(self) -> None:
        for path in [
            "config/linux-builder.toml",
            "docker/linux-builder/**",
            "tools/zed_i18n/linux_builder.py",
            ".github/workflows/i18n-linux-builder.yml",
        ]:
            self.assertIn(path, self.workflow)

        self.assertIn("branches:\n      - master\n", self.workflow.replace("\r\n", "\n"))
        self.assertNotIn("- main", self.workflow)

    def test_all_actions_are_pinned_to_full_commit_shas(self) -> None:
        uses = re.findall(r"^\s*uses:\s*([^\s#]+)", self.workflow, flags=re.MULTILINE)
        self.assertTrue(uses)
        for action in uses:
            self.assertRegex(action, r"^[^@]+@[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
