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
  },
  {
    name: 'notion_search',
    description: 'Search across your Notion workspace',
    inputSchema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Search query' },
        filter_type: { type: 'string', description: 'object type: page or database', enum: ['page', 'database'] },
        page_size: { type: 'number', description: 'Number of results', default: 10 }
      },
      required: ['query']
    },
    server: 'notion'
  },
  {
    name: 'notion_get_page',
    description: 'Fetch a Notion page (metadata only)',
    inputSchema: {
      type: 'object',
      properties: {
        page_id: { type: 'string', description: 'Notion page ID' }
      },
      required: ['page_id']
    },
    server: 'notion'
  },
  {
    name: 'notion_create_page',
    description: 'Create a Notion page under a page or database',
    inputSchema: {
      type: 'object',
      properties: {
        parent: {
          type: 'object',
          description: 'Parent object, e.g., {page_id: \"...\"} or {database_id: \"...\"}'
        },
        properties: {
          type: 'object',
          description: 'Notion properties object (for database pages)'
        },
        children: {
          type: 'array',
          description: 'Notion block children (optional)'
        }
      },
      required: ['parent']
    },
    server: 'notion'
  },
  {
    name: 'notion_update_page',
    description: 'Update Notion page properties',
    inputSchema: {
      type: 'object',
      properties: {
        page_id: { type: 'string', description: 'Page ID' },
        properties: { type: 'object', description: 'Properties to update' }
      },
      required: ['page_id', 'properties']
    },
    server: 'notion'
  },
  {
    name: 'notion_query_database',
    description: 'Query a Notion database',
    inputSchema: {
      type: 'object',
      properties: {
        database_id: { type: 'string' },
        filter: { type: 'object' },
        sorts: { type: 'array' },
        page_size: { type: 'number', default: 100 }
      },
      required: ['database_id']
    },
    server: 'notion'
  },
  {
    name: 'notion_create_database_item',
    description: 'Create an item in a Notion database',
    inputSchema: {
      type: 'object',
      properties: {
        database_id: { type: 'string' },
        properties: { type: 'object' },
        children: { type: 'array' }
      },
      required: ['database_id', 'properties']
    },
    server: 'notion'
  },
  {
    name: 'recraft_generate_image',
    description: 'Generate images using Recraft AI. Supports multiple styles: realistic_image, digital_illustration, vector_illustration, 3d_render, pixel_art, anime, logo, icon, and more.',
    inputSchema: {
      type: 'object',
      properties: {
        prompt: {
          type: 'string',
          description: 'Detailed description of the image to generate'
        },
        style: {
          type: 'string',
          enum: ['realistic_image', 'digital_illustration', 'vector_illustration', '3d_render', 'pixel_art', 'anime', 'logo', 'icon'],
          description: 'Image style (default: realistic_image)',
          default: 'realistic_image'
        },
        model: {
          type: 'string',
          description: 'Model to use (default: recraftv3)',
          default: 'recraftv3'
        },
        n: {
          type: 'number',
          description: 'Number of images to generate (1-4, default: 1)',
          default: 1,
          minimum: 1,
          maximum: 4
        }
      },
      required: ['prompt']
    },
    server: 'recraft'
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

// Notion helpers
function notionHeaders() {
  const apiKey = process.env.NOTION_API_KEY;
  if (!apiKey) {
    throw new Error('NOTION_API_KEY not configured');
  }
  return {
    'Authorization': `Bearer ${apiKey}`,
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
  };
}

async function executeNotionSearch(args) {
  const { query, filter_type, page_size = 10 } = args;
  const headers = notionHeaders();
  const body = { query, page_size: Math.min(page_size, 100) };
  if (filter_type) {
    body.filter = { value: filter_type, property: 'object' };
  }
  const resp = await axios.post('https://api.notion.com/v1/search', body, { headers });
  return [{ type: 'text', text: JSON.stringify(resp.data, null, 2) }];
}

async function executeNotionGetPage(args) {
  const { page_id } = args;
  const headers = notionHeaders();
  const resp = await axios.get(`https://api.notion.com/v1/pages/${page_id}`, { headers });
  return [{ type: 'text', text: JSON.stringify(resp.data, null, 2) }];
}

async function executeNotionCreatePage(args) {
  const headers = notionHeaders();
  const resp = await axios.post('https://api.notion.com/v1/pages', args, { headers });
  return [{ type: 'text', text: JSON.stringify(resp.data, null, 2) }];
}

async function executeNotionUpdatePage(args) {
  const { page_id, properties } = args;
  const headers = notionHeaders();
  const resp = await axios.patch(
    `https://api.notion.com/v1/pages/${page_id}`,
    { properties },
    { headers }
  );
  return [{ type: 'text', text: JSON.stringify(resp.data, null, 2) }];
}

async function executeNotionQueryDatabase(args) {
  const { database_id, filter, sorts, page_size = 100 } = args;
  const headers = notionHeaders();
  const body = { page_size: Math.min(page_size, 100) };
  if (filter) body.filter = filter;
  if (sorts) body.sorts = sorts;
  const resp = await axios.post(
    `https://api.notion.com/v1/databases/${database_id}/query`,
    body,
    { headers }
  );
  return [{ type: 'text', text: JSON.stringify(resp.data, null, 2) }];
}

async function executeNotionCreateDatabaseItem(args) {
  const { database_id, properties, children } = args;
  const headers = notionHeaders();
  const body = {
    parent: { database_id },
    properties
  };
  if (children) body.children = children;
  const resp = await axios.post('https://api.notion.com/v1/pages', body, { headers });
  return [{ type: 'text', text: JSON.stringify(resp.data, null, 2) }];
}

// Recraft helpers
function recraftHeaders() {
  const apiKey = process.env.RECRAFT_API_KEY;
  if (!apiKey) {
    throw new Error('RECRAFT_API_KEY not configured');
  }
  return {
    'Authorization': `Bearer ${apiKey}`,
    'Content-Type': 'application/json'
  };
}

async function executeRecraftGenerateImage(args) {
  const { prompt, style = 'realistic_image', model = 'recraftv3', n = 1 } = args;
  const headers = recraftHeaders();
  
  // Recraft API uses OpenAI-compatible format
  const body = {
    model,
    prompt,
    style,
    n: Math.min(Math.max(1, n), 4), // Clamp between 1-4
    response_format: 'url'
  };
  
  try {
    const resp = await axios.post(
      'https://external.api.recraft.ai/v1/images/generations',
      body,
      { headers }
    );
    
    // Return image URLs and metadata
    const images = resp.data.data || [];
    return [{
      type: 'text',
      text: JSON.stringify({
        success: true,
        images: images.map(img => ({
          url: img.url,
          revised_prompt: img.revised_prompt || prompt
        })),
        style,
        model,
        count: images.length
      }, null, 2)
    }];
  } catch (error) {
    throw new Error(`Recraft API error: ${error.response?.data?.error?.message || error.message}`);
  }
}

const TOOL_EXECUTORS = {
  'brave_web_search': executeBraveSearch,
  'read_file': executeReadFile,
  'list_directory': executeListDirectory,
  'notion_search': executeNotionSearch,
  'notion_get_page': executeNotionGetPage,
  'notion_create_page': executeNotionCreatePage,
  'notion_update_page': executeNotionUpdatePage,
  'notion_query_database': executeNotionQueryDatabase,
  'notion_create_database_item': executeNotionCreateDatabaseItem,
  'recraft_generate_image': executeRecraftGenerateImage
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
  console.log(`\n${'='.repeat(60)}`);
  console.log(`MCP HTTP Bridge v1.0.0 - Started on port ${PORT}`);
  console.log(`${'='.repeat(60)}`);
  console.log(`\nAvailable tools (${TOOLS.length}):`);
  
  // Group tools by server
  const byServer = TOOLS.reduce((acc, t) => {
    const srv = t.server || 'unknown';
    if (!acc[srv]) acc[srv] = [];
    acc[srv].push(t.name);
    return acc;
  }, {});
  
  Object.entries(byServer).forEach(([server, tools]) => {
    console.log(`  [${server}] ${tools.join(', ')}`);
  });
  
  console.log(`\nAPI Key Status:`);
  console.log(`  BRAVE_API_KEY:   ${process.env.BRAVE_API_KEY ? '✓ configured' : '✗ NOT CONFIGURED'}`);
  console.log(`  NOTION_API_KEY:  ${process.env.NOTION_API_KEY ? '✓ configured' : '✗ NOT CONFIGURED'}`);
  console.log(`  RECRAFT_API_KEY: ${process.env.RECRAFT_API_KEY ? '✓ configured' : '✗ NOT CONFIGURED'}`);
  console.log(`\n${'='.repeat(60)}\n`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('Shutting down MCP HTTP Bridge...');
  process.exit(0);
});

