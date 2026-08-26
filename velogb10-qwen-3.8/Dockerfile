ARG CUDA_IMAGE=nvidia/cuda:13.0.2-runtime-ubuntu24.04@sha256:6a0e31b59e70890446f2c17356d6efc0d54260090a8c63d6ca7c2ad049db95d2
FROM ${CUDA_IMAGE}

ARG VELOGB10_VERSION=0.5.0
ARG VELOGB10_RELEASE_SHA256=1d0a564a1874febf34e011c35e6c2fd649239d5af8b838d3fdb41f942fb9b1c7
ARG VELOGB10_SOURCE_COMMIT=89242407e799930e9f4e51559bffc186033d90a7
ARG VELOGB10_LICENSE_SHA256=c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libibverbs1 \
        liblzma5 \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    archive="velogb10-v${VELOGB10_VERSION}-gb10-sm121.tar.gz"; \
    curl --fail --location --retry 3 \
      "https://github.com/sf-stav/veloGB10/releases/download/v${VELOGB10_VERSION}/${archive}" \
      --output "/tmp/${archive}"; \
    printf '%s  %s\n' "${VELOGB10_RELEASE_SHA256}" "/tmp/${archive}" | sha256sum --check --strict; \
    mkdir -p /opt/velogb10; \
    tar --extract --gzip --file "/tmp/${archive}" --directory /opt/velogb10 --strip-components=1; \
    rm "/tmp/${archive}"; \
    test -x /opt/velogb10/gb10_inference; \
    test -f /opt/velogb10/src/ptx/gpu_vision.ptx; \
    mkdir -p /usr/share/licenses/velogb10; \
    curl --fail --location --retry 3 \
      "https://raw.githubusercontent.com/sf-stav/veloGB10/${VELOGB10_SOURCE_COMMIT}/LICENSE" \
      --output /usr/share/licenses/velogb10/LICENSE; \
    printf '%s  %s\n' "${VELOGB10_LICENSE_SHA256}" /usr/share/licenses/velogb10/LICENSE | sha256sum --check --strict; \
    useradd --system --uid 10001 --home-dir /cache --shell /usr/sbin/nologin velogb10; \
    mkdir -p /cache /opt/velogb10/mtp_calib; \
    chown 10001:10001 /cache /opt/velogb10/mtp_calib

LABEL org.opencontainers.image.title="Stacksmith veloGB10 Qwen 3.8 runtime" \
      org.opencontainers.image.description="Pinned veloGB10 binary/PTX release packaged for NVIDIA GB10" \
      org.opencontainers.image.source="https://github.com/sf-stav/veloGB10" \
      org.opencontainers.image.version="${VELOGB10_VERSION}" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.revision="${VELOGB10_SOURCE_COMMIT}"

USER 10001:10001
WORKDIR /opt/velogb10
ENV HOME=/cache \
    XDG_CACHE_HOME=/cache \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

EXPOSE 9000
ENTRYPOINT ["./gb10_inference"]
