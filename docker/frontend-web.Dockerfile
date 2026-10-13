# Multi-stage Dockerfile for Angular HUD Bento SPA
# Build Stage
FROM node:22-alpine AS builder

WORKDIR /app

COPY frontend/web/package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY frontend/web ./
RUN npm run build

# Production Stage with unprivileged Nginx
FROM nginx:1.27-alpine

# Remove default nginx website
RUN rm -rf /usr/share/nginx/html/*

COPY --from=builder /app/dist/valorant-ai-coach-web/browser /usr/share/nginx/html
COPY docker/nginx-spa.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
