FROM node:22-bookworm-slim

ENV PNPM_HOME=/usr/local/share/pnpm \
    PATH="/usr/local/share/pnpm:$PATH"

RUN corepack enable && corepack prepare pnpm@9.15.9 --activate

WORKDIR /repo

COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web/package.json apps/web/package.json

RUN pnpm install --frozen-lockfile

COPY apps/web apps/web

WORKDIR /repo/apps/web
EXPOSE 5173
CMD ["pnpm", "dev"]
