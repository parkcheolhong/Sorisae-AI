# Simple production build for Next.js app router
FROM node:22-alpine AS node_base
RUN set -eux; \
	PICO_URL="$(npm view picomatch@4.0.4 dist.tarball)"; \
	mkdir -p /tmp/pico; \
	wget -qO- "$PICO_URL" | tar -xz -C /tmp/pico; \
	rm -rf /usr/local/lib/node_modules/npm/node_modules/picomatch; \
	mv /tmp/pico/package /usr/local/lib/node_modules/npm/node_modules/picomatch; \
	rm -rf /tmp/pico

FROM node_base AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node_base AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Allow same-origin API via nginx by setting empty NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_API_URL=
ARG NEXT_PUBLIC_SITE_URL=
ARG NEXT_PUBLIC_ADMIN_SITE_ORIGIN=
ARG NEXT_PUBLIC_MARKETPLACE_SITE_ORIGIN=
ARG NEXT_PUBLIC_FORCE_CANONICAL_SITE_HREF=
ARG BACKEND_PROXY_TARGET=http://backend:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL}
ENV NEXT_PUBLIC_ADMIN_SITE_ORIGIN=${NEXT_PUBLIC_ADMIN_SITE_ORIGIN}
ENV NEXT_PUBLIC_MARKETPLACE_SITE_ORIGIN=${NEXT_PUBLIC_MARKETPLACE_SITE_ORIGIN}
ENV NEXT_PUBLIC_FORCE_CANONICAL_SITE_HREF=${NEXT_PUBLIC_FORCE_CANONICAL_SITE_HREF}
ENV BACKEND_PROXY_TARGET=${BACKEND_PROXY_TARGET}
RUN npm run build

FROM node_base AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3005
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/next.config.js ./next.config.js
COPY --from=build /app/.next ./.next
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/public ./public
EXPOSE 3005
CMD ["sh", "-c", "./node_modules/.bin/next start -p ${PORT:-3005}"]
