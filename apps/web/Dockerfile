FROM node:22-bookworm-slim AS build

ENV PNPM_HOME=/usr/local/share/pnpm \
    PATH="/usr/local/share/pnpm:$PATH"

RUN corepack enable && corepack prepare pnpm@9.15.9 --activate

WORKDIR /repo

COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY apps/api/src/hawatch/config/public_pages.json apps/api/src/hawatch/config/public_pages.json
COPY infra/nginx/public-pages.inc infra/nginx/public-pages.inc
COPY infra/nginx/stage-public-pages.inc infra/nginx/stage-public-pages.inc
COPY scripts/generate-public-pages.mjs scripts/generate-public-pages.mjs

RUN pnpm install --frozen-lockfile

COPY apps/web apps/web
COPY apps/api/fixtures/search-normalization.json apps/api/fixtures/search-normalization.json
COPY apps/api/src/hawatch/modules/catalog/templates/catalog/page_load_bootstrap.html apps/api/src/hawatch/modules/catalog/templates/catalog/page_load_bootstrap.html
RUN node scripts/generate-public-pages.mjs --check

WORKDIR /repo/apps/web
ARG VITE_ASSET_VERSION=local
ENV VITE_ASSET_VERSION=${VITE_ASSET_VERSION}
ARG VITE_PUBLIC_ASSET_VERSION=
ENV VITE_PUBLIC_ASSET_VERSION=${VITE_PUBLIC_ASSET_VERSION}
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_GA4_MEASUREMENT_ID=
ARG VITE_QA_PREVIEW=false
ARG VITE_PUBLIC_SITE_ORIGIN=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_GA4_MEASUREMENT_ID=${VITE_GA4_MEASUREMENT_ID} \
    VITE_QA_PREVIEW=${VITE_QA_PREVIEW} \
    VITE_PUBLIC_SITE_ORIGIN=${VITE_PUBLIC_SITE_ORIGIN}
RUN pnpm build

FROM nginx:1.27.5-alpine

COPY --from=build /repo/apps/web/dist /usr/share/nginx/html
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY apps/web/nginx-public-pages.inc /etc/nginx/public-pages.inc
COPY apps/web/nginx-qa-public-pages.inc /etc/nginx/qa-public-pages.inc
COPY apps/web/nginx.qa.conf /tmp/hawatch-qa.conf
COPY apps/web/publish-assets.sh /docker-entrypoint.d/40-publish-assets.sh
RUN chmod +x /docker-entrypoint.d/40-publish-assets.sh
ARG VITE_QA_PREVIEW=false
RUN if [ "$VITE_QA_PREVIEW" = "true" ]; then cp /tmp/hawatch-qa.conf /etc/nginx/conf.d/default.conf; fi \
    && rm /tmp/hawatch-qa.conf

EXPOSE 5173
CMD ["nginx", "-g", "daemon off;"]
