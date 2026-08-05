# syntax=docker/dockerfile:1.7

ARG UBUNTU_BASE
FROM ${UBUNTU_BASE}

ARG RUST_TOOLCHAIN
ARG RUST_PROFILE
ARG RUST_COMPONENTS
ARG RUST_TARGETS
ARG WASI_SDK_VERSION
ARG UV_VERSION
ARG PYTHON_VERSION
ARG BUILD_CONTEXT_SHA256

ENV CARGO_HOME="/opt/cargo" \
    RUSTUP_HOME="/opt/rustup" \
    UV_INSTALL_DIR="/opt/uv" \
    UV_PYTHON_INSTALL_DIR="/opt/uv-python" \
    UV_PROJECT_ENVIRONMENT="/tmp/zed-i18n-venv" \
    UV_NO_PROGRESS="1" \
    CC="clang-18" \
    CXX="clang++-18" \
    PATH="/opt/uv:/opt/cargo/bin:${PATH}"

COPY docker/linux-builder/ubuntu-packages.txt /tmp/ubuntu-packages.txt
COPY docker/linux-builder/install.sh /tmp/install-linux-builder.sh

RUN chmod +x /tmp/install-linux-builder.sh \
    && /tmp/install-linux-builder.sh \
        "${RUST_TOOLCHAIN}" \
        "${RUST_PROFILE}" \
        "${RUST_COMPONENTS}" \
        "${RUST_TARGETS}" \
        "${WASI_SDK_VERSION}" \
        "${UV_VERSION}" \
        "${PYTHON_VERSION}" \
    && rm -f /tmp/install-linux-builder.sh /tmp/ubuntu-packages.txt

COPY docker/linux-builder/run-release.sh /usr/local/bin/zed-i18n-run-linux-release

RUN chmod +x /usr/local/bin/zed-i18n-run-linux-release \
    && rustc --version \
    && cargo --version \
    && uv --version \
    && clang-18 --version \
    && ld.lld --version \
    && llvm-objcopy --version \
    && test -x /opt/wasi-sdk/bin/clang \
    && uv python find "${PYTHON_VERSION}"

LABEL org.opencontainers.image.source="https://github.com/LI-NA/zed-i18n" \
      org.opencontainers.image.description="Reproducible Ubuntu 20.04 build environment for zed-i18n Linux releases" \
      io.zed-i18n.builder.context-sha256="${BUILD_CONTEXT_SHA256}" \
      io.zed-i18n.builder.rust="${RUST_TOOLCHAIN}" \
      io.zed-i18n.builder.wasi-sdk="${WASI_SDK_VERSION}" \
      io.zed-i18n.builder.uv="${UV_VERSION}" \
      io.zed-i18n.builder.python="${PYTHON_VERSION}"

WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/zed-i18n-run-linux-release"]
