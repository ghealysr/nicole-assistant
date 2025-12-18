FROM node:20-slim

WORKDIR /app

# Install Chrome/Chromium and dependencies for Puppeteer
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    chromium \
    fonts-liberation \
    fonts-noto-color-emoji \
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

# Set Puppeteer to use system Chromium instead of downloading its own
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# Copy package.json first for layer caching
COPY package.json /app/

# Install dependencies
RUN npm install --production

# Copy bridge code
COPY mcp-http-bridge.js /app/

# Create data directory for filesystem server
RUN mkdir -p /data && chown -R node:node /data /app

USER node

EXPOSE 3100

CMD ["node", "mcp-http-bridge.js"]

