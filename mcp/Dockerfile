FROM node:20-slim

WORKDIR /app

# Install Chromium dependencies for Puppeteer and wget for healthcheck
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libxshmfence1 \
    xdg-utils \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy package.json first for layer caching
COPY package.json /app/

# Install dependencies (Puppeteer will download Chromium)
RUN npm install --production

# Copy bridge code
COPY mcp-http-bridge.js /app/

# Create data directory for filesystem server
RUN mkdir -p /data && chown -R node:node /data /app

USER node

EXPOSE 3100

CMD ["node", "mcp-http-bridge.js"]

