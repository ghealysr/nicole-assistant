FROM node:20-alpine

WORKDIR /app

# Install wget for healthcheck
RUN apk add --no-cache wget

# Install dependencies
COPY package.json /app/
RUN npm install --production

# Copy bridge code
COPY mcp-http-bridge.js /app/

# Create data directory for filesystem server
RUN mkdir -p /data && chown -R node:node /data /app

USER node

EXPOSE 3100

CMD ["node", "mcp-http-bridge.js"]

