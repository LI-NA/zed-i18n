import shutil
import unittest
from pathlib import Path

from tools.zed_i18n.linux_builder import (
    builder_outputs,
    compute_context_sha256,
    load_builder_config,
    load_builder_environment,
    resolve_manifest,
    validate_image_labels,
    validate_zed_environment,
)


class LinuxBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path.cwd() / "tests" / ".tmp" / self._testMethodName
        shutil.rmtree(self.root, ignore_errors=True)
        (self.root / "config").mkdir(parents=True)
        (self.root / "docker" / "linux-builder").mkdir(parents=True)
        (self.root / "config" / "linux-builder.toml").write_text(
            'image_repository = "ghcr.io/li-na/test-builder"\n'
            'tag_prefix = "focal"\n'
            'context_paths = ["config/linux-builder.toml", "docker/linux-builder"]\n'
            'required_platforms = ["linux/amd64", "linux/arm64"]\n'
            '\n[glibc_max]\n'
            'x86_64 = "2.31"\n'
            'aarch64 = "2.35"\n',
            encoding="utf-8",
        )
        (self.root / "docker" / "linux-builder" / "environment.toml").write_text(
            'ubuntu_base = "ubuntu:20.04@sha256:abc"\n'
            'rust_toolchain = "1.95.0"\n'
            'rust_profile = "minimal"\n'
            'rust_components = ["rustfmt", "clippy"]\n'
            'rust_targets = ["wasm32-wasip2"]\n'
            'wasi_sdk = "25"\n'
            'uv = "0.11.26"\n'
            'python = "3.12"\n',
            encoding="utf-8",
        )
        (self.root / "docker" / "linux-builder" / "Dockerfile").write_text(
            "FROM ubuntu:20.04\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_context_hash_is_deterministic_and_covers_paths_and_contents(self) -> None:
        first = compute_context_sha256(self.root)
        second = compute_context_sha256(self.root)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

        dockerfile = self.root / "docker" / "linux-builder" / "Dockerfile"
        dockerfile.write_text("FROM ubuntu:20.04\nRUN true\n", encoding="utf-8")
        self.assertNotEqual(compute_context_sha256(self.root), first)

        dockerfile.write_text("FROM ubuntu:20.04\n", encoding="utf-8")
        dockerfile.rename(dockerfile.with_name("Containerfile"))
        self.assertNotEqual(compute_context_sha256(self.root), first)

    def test_builder_outputs_use_content_derived_tag_and_pinned_environment(self) -> None:
        context_sha = compute_context_sha256(self.root)

        outputs = builder_outputs(self.root)

        self.assertEqual(outputs["context-sha256"], context_sha)
        self.assertEqual(outputs["image-tag"], f"focal-{context_sha[:16]}")
        self.assertEqual(outputs["image-repository"], "ghcr.io/li-na/test-builder")
        self.assertEqual(outputs["ubuntu-base"], "ubuntu:20.04@sha256:abc")
        self.assertEqual(outputs["rust-toolchain"], "1.95.0")
        self.assertEqual(outputs["rust-components"], "rustfmt,clippy")
        self.assertEqual(outputs["rust-targets"], "wasm32-wasip2")

    def test_loaders_reject_unpinned_base_and_invalid_platforms(self) -> None:
        environment_path = self.root / "docker" / "linux-builder" / "environment.toml"
        environment_path.write_text(
            environment_path.read_text(encoding="utf-8").replace(
                "ubuntu:20.04@sha256:abc", "ubuntu:20.04"
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "digest-pinned"):
            load_builder_environment(self.root)

        config_path = self.root / "config" / "linux-builder.toml"
        config_path.write_text(
            config_path.read_text(encoding="utf-8").replace(
                '"linux/amd64", "linux/arm64"', '"linux/x86_64"'
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "unsupported OCI platform"):
            load_builder_config(self.root)

    def test_resolve_manifest_returns_immutable_reference_for_both_platforms(self) -> None:
        manifest = {
            "schemaVersion": 2,
            "digest": "sha256:" + "c" * 64,
            "manifests": [
                {"digest": "sha256:" + "a" * 64, "platform": {"os": "linux", "architecture": "amd64"}},
                {"digest": "sha256:" + "b" * 64, "platform": {"os": "linux", "architecture": "arm64"}},
            ],
        }
        resolved = resolve_manifest(self.root, manifest)

        self.assertEqual(
            resolved["image"],
            "ghcr.io/li-na/test-builder@sha256:" + "c" * 64,
        )
        self.assertEqual(resolved["digest"], "sha256:" + "c" * 64)

    def test_resolve_manifest_rejects_missing_or_duplicate_platforms(self) -> None:
        digest = "sha256:" + "c" * 64
        amd64 = {
            "digest": "sha256:" + "a" * 64,
            "platform": {"os": "linux", "architecture": "amd64"},
        }

        with self.assertRaisesRegex(ValueError, "missing required platforms: linux/arm64"):
            resolve_manifest(self.root, {"digest": digest, "manifests": [amd64]})

        with self.assertRaisesRegex(ValueError, "duplicate platform"):
            resolve_manifest(self.root, {"digest": digest, "manifests": [amd64, amd64]})

        invalid_arm64 = {
            "digest": "not-a-digest",
            "platform": {"os": "linux", "architecture": "arm64"},
        }
        with self.assertRaisesRegex(ValueError, "invalid descriptor digest for linux/arm64"):
            resolve_manifest(self.root, {"digest": digest, "manifests": [amd64, invalid_arm64]})

    def test_resolve_manifest_rejects_missing_or_invalid_index_digest(self) -> None:
        manifests = [
            {"digest": "sha256:" + "a" * 64, "platform": {"os": "linux", "architecture": "amd64"}},
            {"digest": "sha256:" + "b" * 64, "platform": {"os": "linux", "architecture": "arm64"}},
        ]

        with self.assertRaisesRegex(ValueError, "immutable index digest"):
            resolve_manifest(self.root, {"manifests": manifests})
        with self.assertRaisesRegex(ValueError, "immutable index digest"):
            resolve_manifest(
                self.root,
                {"digest": "focal-test", "manifests": manifests},
            )

    def test_image_labels_must_match_context_and_tool_versions(self) -> None:
        outputs = builder_outputs(self.root)
        labels = {
            "org.opencontainers.image.source": "https://github.com/LI-NA/zed-i18n",
            "io.zed-i18n.builder.context-sha256": outputs["context-sha256"],
            "io.zed-i18n.builder.rust": "1.95.0",
            "io.zed-i18n.builder.wasi-sdk": "25",
            "io.zed-i18n.builder.uv": "0.11.26",
            "io.zed-i18n.builder.python": "3.12",
        }

        validate_image_labels(self.root, labels)

        labels["io.zed-i18n.builder.rust"] = "nightly"
        with self.assertRaisesRegex(ValueError, "rust"):
            validate_image_labels(self.root, labels)

    def test_validates_builder_environment_against_zed_toolchain_files(self) -> None:
        zed_root = self.root / "zed"
        (zed_root / "script").mkdir(parents=True)
        (zed_root / "rust-toolchain.toml").write_text(
            '[toolchain]\n'
            'channel = "1.95.0"\n'
            'profile = "minimal"\n'
            'components = ["rustfmt", "clippy"]\n'
            'targets = ["wasm32-wasip2"]\n',
            encoding="utf-8",
        )
        (zed_root / "script" / "download-wasi-sdk").write_text(
            'WASI_SDK_VERSION="25"\n',
            encoding="utf-8",
        )

        validate_zed_environment(self.root, zed_root)

        toolchain_path = zed_root / "rust-toolchain.toml"
        toolchain_path.write_text(
            toolchain_path.read_text(encoding="utf-8").replace("1.95.0", "nightly"),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "rust_toolchain"):
            validate_zed_environment(self.root, zed_root)


class RepositoryLinuxBuilderContractTests(unittest.TestCase):
    def test_dockerfile_uses_the_pinned_contract_and_records_provenance(self) -> None:
        root = Path.cwd()
        dockerfile = (root / "docker" / "linux-builder" / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("ARG UBUNTU_BASE", dockerfile)
        self.assertIn("FROM ${UBUNTU_BASE}", dockerfile)
        self.assertIn("COPY docker/linux-builder/ubuntu-packages.txt", dockerfile)
        self.assertIn("COPY docker/linux-builder/install.sh", dockerfile)
        self.assertIn("COPY docker/linux-builder/run-release.sh", dockerfile)
        self.assertIn("io.zed-i18n.builder.context-sha256", dockerfile)
        self.assertIn("io.zed-i18n.builder.rust", dockerfile)
        self.assertIn("io.zed-i18n.builder.wasi-sdk", dockerfile)
        self.assertIn("io.zed-i18n.builder.uv", dockerfile)
        self.assertIn("io.zed-i18n.builder.python", dockerfile)
        self.assertIn('CC="clang-18"', dockerfile)
        self.assertIn('CXX="clang++-18"', dockerfile)

    def test_image_package_list_covers_current_zed_ubuntu_dependencies(self) -> None:
        package_file = Path.cwd() / "docker" / "linux-builder" / "ubuntu-packages.txt"
        packages = {
            line.strip()
            for line in package_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        expected = {
            "gcc",
            "g++",
            "libasound2-dev",
            "libfontconfig-dev",
            "libgit2-dev",
            "libglib2.0-dev",
            "libssl-dev",
            "libva-dev",
            "libvulkan1",
            "libwayland-dev",
            "libx11-xcb-dev",
            "libxkbcommon-x11-dev",
            "libzstd-dev",
            "make",
            "jq",
            "git",
            "curl",
            "gettext-base",
            "elfutils",
            "libsqlite3-dev",
            "musl-tools",
            "musl-dev",
            "build-essential",
            "pipewire",
            "xdg-desktop-portal",
            # Zed's script/linux installs the clang/lld/llvm metapackages, which on
            # focal stop at LLVM 10; the image substitutes the versioned LLVM 18
            # packages from apt.llvm.org and symlinks the bare tool names.
            "clang-18",
            "lld-18",
            "llvm-18",
            "libstdc++-11-dev",
        }

        self.assertEqual(expected - packages, set())

    def test_install_script_provides_the_llvm_18_toolchain_on_focal(self) -> None:
        script = (Path.cwd() / "docker" / "linux-builder" / "install.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("apt.llvm.org", script)
        self.assertIn("llvm-toolchain-${codename}-18", script)
        self.assertIn(
            "for tool in clang clang++ ld.lld lld llvm-ar llvm-nm llvm-objcopy "
            "llvm-ranlib llvm-strip; do",
            script,
        )
        self.assertIn('ln -sf "/usr/bin/${tool}-18" "/usr/local/bin/${tool}"', script)

    def test_install_script_pins_a_modern_cmake(self) -> None:
        script = (Path.cwd() / "docker" / "linux-builder" / "install.sh").read_text(
            encoding="utf-8"
        )
        packages = (Path.cwd() / "docker" / "linux-builder" / "ubuntu-packages.txt").read_text(
            encoding="utf-8"
        )

        # focal's apt cmake is 3.16, which predates file(CONFIGURE) required by
        # wasmtime-c-api; the image must use the pinned Kitware binary instead.
        self.assertIn("Kitware/CMake/releases/download", script)
        self.assertRegex(script, r'cmake_version="3\.\d+\.\d+"')
        self.assertIn("ln -sf /opt/cmake/bin/cmake /usr/local/bin/cmake", script)
        self.assertNotIn(
            "cmake",
            [
                line.strip()
                for line in packages.splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ],
        )

    def test_release_script_builds_and_verifies_inside_the_container(self) -> None:
        script = (Path.cwd() / "docker" / "linux-builder" / "run-release.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("tools.zed_i18n.ci_release build-shard", script)
        self.assertIn("tools.zed_i18n.linux_builder validate-zed", script)
        self.assertIn("tools.zed_i18n.linux_abi", script)
        # Linux matrix entries always ship an empty bundle_target, so the script
        # must not require it.
        self.assertIn('BUNDLE_TARGET="${BUNDLE_TARGET:-}"', script)
        self.assertNotIn("BUNDLE_TARGET:?", script)
        self.assertIn("/opt/wasi-sdk", script)
        self.assertIn("UV_PROJECT_ENVIRONMENT", script)
        self.assertNotIn("sudo", script)


if __name__ == "__main__":
    unittest.main()
