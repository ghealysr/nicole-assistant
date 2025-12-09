# Nicole V7 MCP HTTP Bridge

This directory contains the HTTP bridge that exposes Model Context Protocol (MCP) servers over HTTP/JSON-RPC for Nicole V7.

## Architecture

```
[Nicole Backend] → HTTP/JSON-RPC → [MCP HTTP Bridge] → stdio → [MCP Servers]
```

The bridge:
- Exposes a unified HTTP/JSON-RPC interface on port 3100
- Spawns and manages MCP servers as child processes
- Translates HTTP requests to stdio-based JSON-RPC
- Aggregates tools from multiple MCP servers

## Files

- `mcp-http-bridge.js` - Main bridge implementation
- `package.json` - Node.js dependencies
- `Dockerfile` - Container definition
- `docker-compose.yml` - Service orchestration

## MCP Servers Included

1. **Brave Search** - Web search via Brave Search API
2. **Filesystem** - Safe file operations in `/data`

## Environment Variables

- `BRAVE_API_KEY` - Required for Brave Search MCP server
- `PORT` - HTTP server port (default: 3100)

## Deployment

### On Production (Linux droplet):

```bash
# 1. Navigate to MCP directory
cd /opt/nicole/mcp

# 2. Ensure .env has BRAVE_API_KEY
grep BRAVE_API_KEY /opt/nicole/.env

# 3. Build and start the bridge
docker compose build
docker compose up -d

# 4. Verify health
curl http://127.0.0.1:3100/health

# 5. Test tools listing
curl -X POST http://127.0.0.1:3100/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

### Check Logs:

```bash
docker logs -f nicole-mcp-bridge
```

### Restart:

```bash
docker compose restart
```

## Backend Integration

The bridge is automatically connected by Nicole's backend via:
- `backend/app/mcp/docker_mcp_client.py` - Python client
- `backend/app/main.py` - Lifecycle management
- `backend/app/routers/alphawave_health.py` - Health endpoint

## Troubleshooting

**Bridge won't start:**
- Check Docker logs: `docker logs nicole-mcp-bridge`
- Verify port 3100 is not in use: `ss -tlnp | grep 3100`

**No tools found:**
- Ensure MCP server packages are installed (they're in package.json)
- Check if npm can access the MCP registry
- Look for errors in bridge logs

**Brave Search fails:**
- Verify `BRAVE_API_KEY` is set in `/opt/nicole/.env`
- Check the key is valid at https://brave.com/search/api/

## Security Notes

- Port 3100 is bound to `127.0.0.1` only (localhost)
- Not exposed to external network
- Filesystem server has read-only access to `/data`
- Runs as non-root user inside container

