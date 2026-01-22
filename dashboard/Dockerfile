# =============================================================================
# MERIDIAN Dashboard - Production Dockerfile
# =============================================================================
# Multi-stage build for optimized React/Vite container
# =============================================================================

# Build stage
FROM node:20-alpine as builder

WORKDIR /app

# Build arguments for API configuration
ARG VITE_API_URL=http://localhost:8000
ARG VITE_WS_URL=ws://localhost:8000/ws
ARG VITE_PROJECT_PATH=/app/workspace

ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL
ENV VITE_PROJECT_PATH=$VITE_PROJECT_PATH

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci --silent

# Copy source and build
COPY . .
RUN npm run build

# -----------------------------------------------------------------------------
# Production stage - Nginx
# -----------------------------------------------------------------------------
FROM nginx:alpine as production

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Custom nginx config for SPA routing
RUN cat > /etc/nginx/conf.d/default.conf << 'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private auth;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml application/javascript;

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA fallback - all routes go to index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "OK\n";
        add_header Content-Type text/plain;
    }

    # API proxy (optional - if dashboard and API on same domain)
    # Uncomment and configure if needed:
    # location /api/ {
    #     proxy_pass http://api:8000/;
    #     proxy_http_version 1.1;
    #     proxy_set_header Upgrade $http_upgrade;
    #     proxy_set_header Connection "upgrade";
    #     proxy_set_header Host $host;
    #     proxy_set_header X-Real-IP $remote_addr;
    #     proxy_cache_bypass $http_upgrade;
    # }
}
EOF

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:80/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
