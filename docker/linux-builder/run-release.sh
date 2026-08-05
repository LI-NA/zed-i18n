#!/usr/bin/env bash
set -euo pipefail

: "${ZED_VERSION:?ZED_VERSION is required}"
: "${LANGUAGES:?LANGUAGES is required}"
: "${ARCH:?ARCH is required}"
: "${DISTRIBUTION_PATCHES_ENABLED:?DISTRIBUTION_PATCHES_ENABLED is required}"
# Linux builds carry no bundle target; only macOS matrix entries set one.
BUNDLE_TARGET="${BUNDLE_TARGET:-}"

case "${ARCH}:$(uname -m)" in
    x86_64:x86_64|aarch64:aarch64|aarch64:arm64) ;;
    *) echo "Container architecture does not match requested build architecture: ${ARCH}:$(uname -m)" >&2; exit 1 ;;
esac

workspace="/workspace"
zed_root="${workspace}/.cache/zed/${ZED_VERSION}"
dist_dir="${DIST_DIR:-dist}"
export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-/tmp/zed-i18n-venv}"

test -d "${zed_root}"
mkdir -p "${HOME}" "${CARGO_HOME}"
git config --global --add safe.directory "${workspace}"
git config --global --add safe.directory "${zed_root}"

if [[ -e "${zed_root}/target/wasi-sdk" && ! -L "${zed_root}/target/wasi-sdk" ]]; then
    echo "Expected ${zed_root}/target/wasi-sdk to be absent or a symlink" >&2
    exit 1
fi
mkdir -p "${zed_root}/target"
ln -sfn /opt/wasi-sdk "${zed_root}/target/wasi-sdk"

distribution_args=()
if [[ "${DISTRIBUTION_PATCHES_ENABLED}" == "true" ]]; then
    distribution_args=(--distribution-config config/distribution.toml)
fi

cd "${workspace}"
uv run --frozen python -m tools.zed_i18n.linux_builder validate-zed --zed-root "${zed_root}"
uv run --frozen python -m tools.zed_i18n.ci_release build-shard \
    --platform linux \
    --arch "${ARCH}" \
    --bundle-target "${BUNDLE_TARGET}" \
    --languages "${LANGUAGES}" \
    --dist-dir "${dist_dir}" \
    "${distribution_args[@]}"

shopt -s nullglob
archives=("${dist_dir}"/*-linux-"${ARCH}".tar.gz)
if [[ "${#archives[@]}" -eq 0 ]]; then
    echo "No Linux release archives were produced in ${dist_dir}" >&2
    exit 1
fi
uv run --frozen python -m tools.zed_i18n.linux_abi --arch "${ARCH}" "${archives[@]}"
