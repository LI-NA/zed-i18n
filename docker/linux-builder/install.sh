#!/usr/bin/env bash
set -euo pipefail

rust_toolchain="${1:?missing Rust toolchain}"
rust_profile="${2:?missing Rust profile}"
rust_components_csv="${3:?missing Rust components}"
rust_targets_csv="${4:?missing Rust targets}"
wasi_sdk_version="${5:?missing WASI SDK version}"
uv_version="${6:?missing uv version}"
python_version="${7:?missing Python version}"

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install --yes --no-install-recommends ca-certificates curl gnupg lsb-release

codename="$(lsb_release -cs)"
echo "deb https://ppa.launchpadcontent.net/ubuntu-toolchain-r/test/ubuntu ${codename} main" \
    > /etc/apt/sources.list.d/ubuntu-toolchain-r-test.list
curl -fsSL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x1E9377A2BA9EF27F" \
    | sed -n "/-----BEGIN PGP PUBLIC KEY BLOCK-----/,/-----END PGP PUBLIC KEY BLOCK-----/p" \
    | gpg --dearmor -o /etc/apt/trusted.gpg.d/ubuntu-toolchain-r-test.gpg

# The Ubuntu 20.04 archives stop at clang-12 and the toolchain-r PPA only carries
# GCC, so the clang-18 toolchain Zed requires comes from apt.llvm.org.
echo "deb https://apt.llvm.org/${codename}/ llvm-toolchain-${codename}-18 main" \
    > /etc/apt/sources.list.d/apt-llvm-org.list
curl -fsSL "https://apt.llvm.org/llvm-snapshot.gpg.key" \
    | gpg --dearmor -o /etc/apt/trusted.gpg.d/apt-llvm-org.gpg

mapfile -t packages < <(sed -e '/^[[:space:]]*#/d' -e '/^[[:space:]]*$/d' /tmp/ubuntu-packages.txt)
apt-get update
apt-get install --yes --no-install-recommends "${packages[@]}"
rm -rf /var/lib/apt/lists/*

# script/bundle-linux and gcc's -fuse-ld=lld resolve bare tool names, and focal's
# clang/lld/llvm metapackages would pin them to LLVM 10.
for tool in clang clang++ ld.lld lld llvm-ar llvm-nm llvm-objcopy llvm-ranlib llvm-strip; do
    test -x "/usr/bin/${tool}-18"
    ln -sf "/usr/bin/${tool}-18" "/usr/local/bin/${tool}"
done

# focal's cmake 3.16 predates file(CONFIGURE), which wasmtime-c-api's build
# scripts require; install the pinned Kitware binary instead.
cmake_version="3.31.12"
case "$(uname -m)" in
    x86_64) cmake_arch="x86_64" ;;
    aarch64|arm64) cmake_arch="aarch64" ;;
    *) echo "Unsupported image architecture: $(uname -m)" >&2; exit 1 ;;
esac
cmake_archive="cmake-${cmake_version}-linux-${cmake_arch}.tar.gz"
curl -fL \
    "https://github.com/Kitware/CMake/releases/download/v${cmake_version}/${cmake_archive}" \
    -o "/tmp/${cmake_archive}"
tar -xzf "/tmp/${cmake_archive}" -C /opt
mv "/opt/cmake-${cmake_version}-linux-${cmake_arch}" /opt/cmake
ln -sf /opt/cmake/bin/cmake /usr/local/bin/cmake
rm -f "/tmp/${cmake_archive}"

curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
    | sh -s -- -y --no-modify-path --profile "${rust_profile}" --default-toolchain "${rust_toolchain}"
IFS=',' read -r -a rust_components <<< "${rust_components_csv}"
IFS=',' read -r -a rust_targets <<< "${rust_targets_csv}"
rustup component add --toolchain "${rust_toolchain}" "${rust_components[@]}"
rustup target add --toolchain "${rust_toolchain}" "${rust_targets[@]}"

curl -LsSf "https://astral.sh/uv/${uv_version}/install.sh" | sh
uv python install "${python_version}"

case "$(uname -m)" in
    x86_64) wasi_arch="x86_64" ;;
    aarch64|arm64) wasi_arch="arm64" ;;
    *) echo "Unsupported image architecture: $(uname -m)" >&2; exit 1 ;;
esac
wasi_archive="wasi-sdk-${wasi_sdk_version}.0-${wasi_arch}-linux.tar.gz"
curl -fL \
    "https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-${wasi_sdk_version}/${wasi_archive}" \
    -o "/tmp/${wasi_archive}"
tar -xzf "/tmp/${wasi_archive}" -C /opt
mv "/opt/wasi-sdk-${wasi_sdk_version}.0-${wasi_arch}-linux" /opt/wasi-sdk
rm -f "/tmp/${wasi_archive}"
