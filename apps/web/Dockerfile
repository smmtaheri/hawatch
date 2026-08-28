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
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN pnpm build

FROM nginx:1.27-alpine

COPY --from=build /repo/apps/web/dist /usr/share/nginx/html
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 5173
CMD ["nginx", "-g", "daemon off;"]
