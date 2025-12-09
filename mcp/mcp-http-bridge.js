#!/usr/bin/env node

/**
 * MCP HTTP Bridge - Stub Implementation
 * 
 * Provides HTTP/JSON-RPC interface for MCP tools.
 * This is a stub implementation until official MCP servers are available.
 */

const express = require('express');
const axios = require('axios');
const { v4: uuidv4 } = require('uuid');
const { readdir, readFile, stat } = require('fs').promises;
const { join } = require('path');

const app = express();
app.use(express.json());

// Tool implementations
const TOOLS = [
  {
    name: 'brave_web_search',
    description: 'Search the web using Brave Search API. Returns recent, relevant web results.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Search query'
        },
        count: {
          type: 'number',
          description: 'Number of results (1-20, default 10)',
          default: 10
        }
      },
      required: ['query']
    },
    server: 'brave-search'
  },
  {
    name: 'read_file',
    description: 'Read contents of a file from the /data directory',
    inputSchema: {
      type: 'object',
      properties: {
        path: {
          type: 'string',
          description: 'File path relative to /data'
        }
      },
      required: ['path']
    },
    server: 'filesystem'
  },
  {
    name: 'list_directory',
    description: 'List files and directories in /data',
    inputSchema: {
      type: 'object',
      properties: {
        path: {
          type: 'string',
          description: 'Directory path relative to /data (default: ".")',
          default: '.'
        }
      }
    },
    server: 'filesystem'
  }
];

// Tool execution handlers
async function executeBraveSearch(args) {
  const apiKey = process.env.BRAVE_API_KEY;
  if (!apiKey) {
    throw new Error('BRAVE_API_KEY not configured');
  }

  const { query, count = 10 } = args;
  
  try {
    const response = await axios.get('https://api.search.brave.com/res/v1/web/search', {
      headers: {
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip',
        'X-Subscription-Token': apiKey
      },
      params: {
        q: query,
        count: Math.min(count, 20)
      }
    });

    const results = response.data.web?.results || [];
    const formatted = results.map(r => ({
      title: r.title,
      url: r.url,
      description: r.description
    }));

    return [{
      type: 'text',
      text: JSON.stringify(formatted, null, 2)
    }];
  } catch (error) {
    throw new Error(`Brave Search failed: ${error.message}`);
  }
}

async function executeReadFile(args) {
  const { path } = args;
  const fullPath = join('/data', path);

  // Security: prevent path traversal
  if (!fullPath.startsWith('/data/')) {
    throw new Error('Access denied: path must be within /data');
  }

  try {
    const content = await readFile(fullPath, 'utf-8');
    return [{
      type: 'text',
      text: content
    }];
  } catch (error) {
    throw new Error(`Failed to read file: ${error.message}`);
  }
}

async function executeListDirectory(args) {
  const { path = '.' } = args;
  const fullPath = join('/data', path);

  // Security: prevent path traversal
  if (!fullPath.startsWith('/data')) {
    throw new Error('Access denied: path must be within /data');
  }

  try {
    const entries = await readdir(fullPath, { withFileTypes: true });
    const formatted = await Promise.all(
      entries.map(async (entry) => {
        const entryPath = join(fullPath, entry.name);
        const stats = await stat(entryPath);
        return {
          name: entry.name,
          type: entry.isDirectory() ? 'directory' : 'file',
          size: stats.size,
          modified: stats.mtime.toISOString()
        };
      })
    );

    return [{
      type: 'text',
      text: JSON.stringify(formatted, null, 2)
    }];
  } catch (error) {
    throw new Error(`Failed to list directory: ${error.message}`);
  }
}

const TOOL_EXECUTORS = {
  'brave_web_search': executeBraveSearch,
  'read_file': executeReadFile,
  'list_directory': executeListDirectory
};


// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    bridge: 'mcp-http-bridge',
    version: '1.0.0',
    tools: TOOLS.length
  });
});

// JSON-RPC endpoint
app.post('/rpc', async (req, res) => {
  try {
    const { jsonrpc, method, params, id } = req.body;

    if (method === 'tools/list') {
      return res.json({
        jsonrpc: '2.0',
        id,
        result: { tools: TOOLS }
      });
    }

    if (method === 'tools/call') {
      const toolName = params?.name;
      const toolArgs = params?.arguments || {};

      if (!toolName) {
        return res.status(400).json({
          jsonrpc: '2.0',
          id,
          error: { code: -32602, message: 'Missing tool name' }
        });
      }

      const executor = TOOL_EXECUTORS[toolName];
      if (!executor) {
        return res.status(404).json({
          jsonrpc: '2.0',
          id,
          error: { code: -32601, message: `Tool not found: ${toolName}` }
        });
      }

      try {
        const result = await executor(toolArgs);
        return res.json({
          jsonrpc: '2.0',
          id,
          result: { content: result }
        });
      } catch (error) {
        console.error(`Tool execution error (${toolName}):`, error.message);
        return res.status(500).json({
          jsonrpc: '2.0',
          id,
          error: { code: -32000, message: error.message }
        });
      }
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
  console.log(`Available tools: ${TOOLS.map(t => t.name).join(', ')}`);
  console.log(`Brave API Key: ${process.env.BRAVE_API_KEY ? 'configured' : 'NOT CONFIGURED'}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('Shutting down MCP HTTP Bridge...');
  process.exit(0);
});

