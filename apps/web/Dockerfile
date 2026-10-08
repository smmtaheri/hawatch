FROM node:22-bookworm-slim AS build

ENV PNPM_HOME=/usr/local/share/pnpm \
    PATH="/usr/local/share/pnpm:$PATH"

RUN corepack enable && corepack prepare pnpm@9.15.9 --activate

WORKDIR /repo

COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web/package.json apps/web/package.json

RUN pnpm install --frozen-lockfile

COPY apps/web apps/web

WORKDIR /repo/apps/web
ARG VITE_ASSET_VERSION=local
ENV VITE_ASSET_VERSION=${VITE_ASSET_VERSION}
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_QA_PREVIEW=false
ARG VITE_PUBLIC_SITE_ORIGIN=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_QA_PREVIEW=${VITE_QA_PREVIEW} \
    VITE_PUBLIC_SITE_ORIGIN=${VITE_PUBLIC_SITE_ORIGIN}
RUN pnpm build

FROM nginx:1.27-alpine

COPY --from=build /repo/apps/web/dist /usr/share/nginx/html
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY apps/web/nginx.qa.conf /tmp/hawatch-qa.conf
ARG VITE_QA_PREVIEW=false
RUN if [ "$VITE_QA_PREVIEW" = "true" ]; then cp /tmp/hawatch-qa.conf /etc/nginx/conf.d/default.conf; fi \
    && rm /tmp/hawatch-qa.conf

EXPOSE 5173
CMD ["nginx", "-g", "daemon off;"]
