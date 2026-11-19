# A clean Linux box with everything pr-evidence needs, for proving the skill is
# portable: build it, then run tests/pr-evidence/test.sh inside, or start an
# agent (codex) inside and let it follow the skill end to end.
#
#   docker build -t pr-evidence-linux tests/pr-evidence
#   docker run --rm -v "$PWD:/repo:ro" pr-evidence-linux bash /repo/tests/pr-evidence/test.sh
FROM debian:trixie-slim

ARG GH_VERSION=2.105.0
ARG SHUX_VERSION=v0.57.2
ARG CODEX_VERSION=0.170.0

RUN apt-get update && apt-get install -y --no-install-recommends \
      bash ca-certificates curl git jq ffmpeg perl python3 procps \
      fonts-dejavu-core fonts-jetbrains-mono fontconfig shellcheck \
      sudo less \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /uvx /usr/local/bin/
# Node 22+: the skills CLI (npx skills add) uses fs/promises glob; Debian ships 20.
COPY --from=node:22-trixie-slim /usr/local/bin/ /usr/local/bin/
COPY --from=node:22-trixie-slim /usr/local/lib/node_modules/ /usr/local/lib/node_modules/

RUN arch=$(dpkg --print-architecture) \
    && curl -fsSL "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${arch}.tar.gz" \
       | tar -xz -C /tmp \
    && install -m 755 "/tmp/gh_${GH_VERSION}_linux_${arch}/bin/gh" /usr/local/bin/gh \
    && rm -rf /tmp/gh_*

RUN npm install -g "@openai/codex@${CODEX_VERSION}" && npm cache clean --force

RUN useradd -m -s /bin/bash dev && echo 'dev ALL=(ALL) NOPASSWD:ALL' >/etc/sudoers.d/dev
USER dev
WORKDIR /home/dev
ENV PATH=/home/dev/.local/bin:$PATH TERM=xterm-256color COLORTERM=truecolor
RUN curl -fsSL https://shux.pages.dev/install.sh | sh -s -- --version "${SHUX_VERSION}" --no-skill
