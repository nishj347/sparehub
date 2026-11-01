# Multi-stage build for SpareHub Frontend
# Stage 1: Build static distribution files
FROM node:20-alpine AS builder

WORKDIR /app

# Install npm dependencies
COPY package*.json ./
RUN npm ci

# Copy frontend source code
COPY . .

# Build argument for VITE_API_BASE_URL (defaults to /api for production nginx proxy)
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# Stage 2: Serve static distribution with unprivileged Nginx
FROM nginxinc/nginx-unprivileged:alpine

# Copy built static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy Nginx default configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Healthcheck for nginx container
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]

