#!/usr/bin/env node

/**
 * MCP HTTP Bridge
 * 
 * Exposes MCP servers (stdio-based) over HTTP with JSON-RPC interface.
 * Usage: node mcp-http-bridge.js
 */

const express = require('express');
const { spawn } = require('child_process');
const { v4: uuidv4 } = require('uuid');

const app = express();
app.use(express.json());

// MCP Server Configuration
const MCP_SERVERS = {
  'brave-search': {
    command: 'npx',
    args: ['@modelcontextprotocol/server-brave-search'],
    env: { BRAVE_API_KEY: process.env.BRAVE_API_KEY }
  },
  'filesystem': {
    command: 'npx',
    args: ['@modelcontextprotocol/server-filesystem', '/data'],
    env: {}
  }
};

// Active MCP server processes
const serverProcesses = new Map();

/**
 * Start an MCP server process
 */
function startServer(serverId) {
  const config = MCP_SERVERS[serverId];
  if (!config) {
    throw new Error(`Unknown server: ${serverId}`);
  }

  console.log(`[${serverId}] Starting MCP server...`);

  const process = spawn(config.command, config.args, {
    env: { ...process.env, ...config.env },
    stdio: ['pipe', 'pipe', 'pipe']
  });

  const serverState = {
    process,
    pendingRequests: new Map(),
    buffer: ''
  };

  // Handle stdout (responses from MCP server)
  process.stdout.on('data', (data) => {
    serverState.buffer += data.toString();
    
    // Try to parse complete JSON-RPC messages
    const lines = serverState.buffer.split('\n');
    serverState.buffer = lines.pop(); // Keep incomplete line

    for (const line of lines) {
      if (!line.trim()) continue;
      
      try {
        const response = JSON.parse(line);
        const requestId = response.id || response.result?.id;
        
        if (requestId && serverState.pendingRequests.has(requestId)) {
          const { resolve } = serverState.pendingRequests.get(requestId);
          resolve(response);
          serverState.pendingRequests.delete(requestId);
        }
      } catch (err) {
        console.error(`[${serverId}] Failed to parse response:`, err.message);
      }
    }
  });

  // Handle stderr (errors/logs)
  process.stderr.on('data', (data) => {
    console.error(`[${serverId}] stderr:`, data.toString());
  });

  // Handle process exit
  process.on('exit', (code) => {
    console.log(`[${serverId}] Process exited with code ${code}`);
    serverProcesses.delete(serverId);
  });

  serverProcesses.set(serverId, serverState);
  console.log(`[${serverId}] MCP server started`);
}

/**
 * Send JSON-RPC request to MCP server
 */
function sendToServer(serverId, jsonRpcRequest) {
  return new Promise((resolve, reject) => {
    const serverState = serverProcesses.get(serverId);
    if (!serverState) {
      return reject(new Error(`Server ${serverId} not running`));
    }

    const requestId = jsonRpcRequest.id || uuidv4();
    const requestWithId = { ...jsonRpcRequest, id: requestId };

    // Store pending request
    serverState.pendingRequests.set(requestId, { resolve, reject });

    // Send to MCP server
    serverState.process.stdin.write(JSON.stringify(requestWithId) + '\n');

    // Timeout after 30 seconds
    setTimeout(() => {
      if (serverState.pendingRequests.has(requestId)) {
        serverState.pendingRequests.delete(requestId);
        reject(new Error('Request timeout'));
      }
    }, 30000);
  });
}

// Health check endpoint
app.get('/health', (req, res) => {
  const status = {
    status: 'healthy',
    servers: {}
  };

  for (const [serverId, state] of serverProcesses.entries()) {
    status.servers[serverId] = {
      running: true,
      pid: state.process.pid
    };
  }

  res.json(status);
});

// JSON-RPC endpoint
app.post('/rpc', async (req, res) => {
  try {
    const { jsonrpc, method, params, id } = req.body;

    if (method === 'tools/list') {
      // Aggregate tools from all servers
      const allTools = [];

      for (const serverId of Object.keys(MCP_SERVERS)) {
        try {
          if (!serverProcesses.has(serverId)) {
            startServer(serverId);
            // Give server time to start
            await new Promise(resolve => setTimeout(resolve, 2000));
          }

          const response = await sendToServer(serverId, {
            jsonrpc: '2.0',
            method: 'tools/list',
            id: uuidv4()
          });

          if (response.result?.tools) {
            const tools = response.result.tools.map(tool => ({
              ...tool,
              _server: serverId
            }));
            allTools.push(...tools);
          }
        } catch (err) {
          console.error(`Failed to get tools from ${serverId}:`, err.message);
        }
      }

      return res.json({
        jsonrpc: '2.0',
        id,
        result: { tools: allTools }
      });
    }

    if (method === 'tools/call') {
      // Find which server has this tool
      const toolName = params?.name;
      if (!toolName) {
        return res.status(400).json({
          jsonrpc: '2.0',
          id,
          error: { code: -32602, message: 'Missing tool name' }
        });
      }

      // Try each server until we find the tool
      for (const serverId of Object.keys(MCP_SERVERS)) {
        try {
          if (!serverProcesses.has(serverId)) {
            startServer(serverId);
            await new Promise(resolve => setTimeout(resolve, 2000));
          }

          const response = await sendToServer(serverId, {
            jsonrpc: '2.0',
            method: 'tools/call',
            params,
            id: uuidv4()
          });

          if (response.result) {
            return res.json({
              jsonrpc: '2.0',
              id,
              result: response.result
            });
          }
        } catch (err) {
          console.error(`Failed to call tool on ${serverId}:`, err.message);
        }
      }

      return res.status(404).json({
        jsonrpc: '2.0',
        id,
        error: { code: -32601, message: `Tool not found: ${toolName}` }
      });
    }

    return res.status(400).json({
      jsonrpc: '2.0',
      id,
      error: { code: -32601, message: `Unknown method: ${method}` }
    });

  } catch (err) {
    console.error('RPC error:', err);
    res.status(500).json({
      jsonrpc: '2.0',
      id: req.body.id,
      error: { code: -32603, message: err.message }
    });
  }
});

// Start the bridge
const PORT = process.env.PORT || 3100;
app.listen(PORT, '0.0.0.0', () => {
  console.log(`MCP HTTP Bridge listening on port ${PORT}`);
  console.log(`Available servers: ${Object.keys(MCP_SERVERS).join(', ')}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('Shutting down...');
  for (const [serverId, state] of serverProcesses.entries()) {
    console.log(`Stopping ${serverId}...`);
    state.process.kill();
  }
  process.exit(0);
});

