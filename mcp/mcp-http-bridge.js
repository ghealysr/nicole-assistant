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
const puppeteer = require('puppeteer');
const { google } = require('googleapis');

// Puppeteer browser instance (lazy loaded)
let browser = null;
let currentPage = null;

async function getBrowser() {
  if (!browser) {
    // Use system Chromium if available (Docker), otherwise let Puppeteer find it
    const executablePath = process.env.PUPPETEER_EXECUTABLE_PATH || undefined;
    
    browser = await puppeteer.launch({
      headless: 'new',
      executablePath,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--single-process',
        '--disable-software-rasterizer'
      ]
    });
    console.log(`[Puppeteer] Browser launched (executable: ${executablePath || 'bundled'})`);
  }
  return browser;
}

async function getPage() {
  const b = await getBrowser();
  if (!currentPage || currentPage.isClosed()) {
    currentPage = await b.newPage();
    await currentPage.setViewport({ width: 1280, height: 800 });
    console.log('[Puppeteer] New page created');
  }
  return currentPage;
}

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
  },
  {
    name: 'puppeteer_navigate',
    description: 'Navigate to a URL using a headless browser. Use this before taking screenshots.',
    inputSchema: {
      type: 'object',
      properties: {
        url: {
          type: 'string',
          description: 'URL to navigate to'
        },
        waitUntil: {
          type: 'string',
          enum: ['load', 'domcontentloaded', 'networkidle0', 'networkidle2'],
          description: 'When to consider navigation complete (default: networkidle2)',
          default: 'networkidle2'
        }
      },
      required: ['url']
    },
    server: 'puppeteer'
  },
  {
    name: 'puppeteer_screenshot',
    description: 'Take a screenshot of the current page. Must navigate first with puppeteer_navigate.',
    inputSchema: {
      type: 'object',
      properties: {
        fullPage: {
          type: 'boolean',
          description: 'Capture full scrollable page (default: false)',
          default: false
        },
        type: {
          type: 'string',
          enum: ['png', 'jpeg', 'webp'],
          description: 'Image format (default: png)',
          default: 'png'
        }
      }
    },
    server: 'puppeteer'
  },
  {
    name: 'puppeteer_evaluate',
    description: 'Execute JavaScript code in the browser context and return the result. Useful for scraping, running axe-core, or injecting scripts.',
    inputSchema: {
      type: 'object',
      properties: {
        script: {
          type: 'string',
          description: 'JavaScript code to execute in browser context. Must return a Promise or value.'
        }
      },
      required: ['script']
    },
    server: 'puppeteer'
  },
  {
    name: 'github_create_repo',
    description: 'Create a new GitHub repository. Returns the repository URL and clone URL.',
    inputSchema: {
      type: 'object',
      properties: {
        name: {
          type: 'string',
          description: 'Repository name (lowercase, hyphens allowed)'
        },
        description: {
          type: 'string',
          description: 'Repository description'
        },
        private: {
          type: 'boolean',
          description: 'Make repository private (default: true)',
          default: true
        }
      },
      required: ['name']
    },
    server: 'github'
  },
  {
    name: 'github_push_files',
    description: 'Push multiple files to a GitHub repository in a single commit.',
    inputSchema: {
      type: 'object',
      properties: {
        repo: {
          type: 'string',
          description: 'Repository name'
        },
        files: {
          type: 'array',
          description: 'Array of {path, content} objects',
          items: {
            type: 'object',
            properties: {
              path: { type: 'string' },
              content: { type: 'string' }
            }
          }
        },
        message: {
          type: 'string',
          description: 'Commit message',
          default: 'Update from Vibe'
        },
        branch: {
          type: 'string',
          description: 'Target branch',
          default: 'main'
        }
      },
      required: ['repo', 'files']
    },
    server: 'github'
  },
  // Gmail Tools
  {
    name: 'gmail_list_messages',
    description: 'List Gmail messages matching a query. Returns message IDs and snippets.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Gmail search query (e.g., "is:unread", "from:example@gmail.com", "subject:important")'
        },
        maxResults: {
          type: 'number',
          description: 'Maximum number of messages to return (1-100, default 10)',
          default: 10
        },
        account: {
          type: 'number',
          description: 'Account number (1, 2, or 3 for multiple accounts, default 1)',
          default: 1
        }
      }
    },
    server: 'gmail'
  },
  {
    name: 'gmail_get_message',
    description: 'Get full details of a specific Gmail message including body and attachments.',
    inputSchema: {
      type: 'object',
      properties: {
        messageId: {
          type: 'string',
          description: 'The message ID to retrieve'
        },
        account: {
          type: 'number',
          description: 'Account number (1, 2, or 3)',
          default: 1
        }
      },
      required: ['messageId']
    },
    server: 'gmail'
  },
  {
    name: 'gmail_send_message',
    description: 'Send an email via Gmail.',
    inputSchema: {
      type: 'object',
      properties: {
        to: {
          type: 'string',
          description: 'Recipient email address(es), comma-separated for multiple'
        },
        subject: {
          type: 'string',
          description: 'Email subject'
        },
        body: {
          type: 'string',
          description: 'Email body (plain text or HTML)'
        },
        cc: {
          type: 'string',
          description: 'CC recipients, comma-separated'
        },
        bcc: {
          type: 'string',
          description: 'BCC recipients, comma-separated'
        },
        isHtml: {
          type: 'boolean',
          description: 'Whether body is HTML (default: false)',
          default: false
        },
        account: {
          type: 'number',
          description: 'Account number (1, 2, or 3)',
          default: 1
        }
      },
      required: ['to', 'subject', 'body']
    },
    server: 'gmail'
  },
  {
    name: 'gmail_reply_to_message',
    description: 'Reply to an existing Gmail message.',
    inputSchema: {
      type: 'object',
      properties: {
        messageId: {
          type: 'string',
          description: 'The message ID to reply to'
        },
        body: {
          type: 'string',
          description: 'Reply body'
        },
        isHtml: {
          type: 'boolean',
          description: 'Whether body is HTML',
          default: false
        },
        account: {
          type: 'number',
          description: 'Account number',
          default: 1
        }
      },
      required: ['messageId', 'body']
    },
    server: 'gmail'
  },
  {
    name: 'gmail_modify_labels',
    description: 'Add or remove labels from a Gmail message (mark read/unread, archive, star, etc.).',
    inputSchema: {
      type: 'object',
      properties: {
        messageId: {
          type: 'string',
          description: 'The message ID'
        },
        addLabels: {
          type: 'array',
          items: { type: 'string' },
          description: 'Labels to add (e.g., ["STARRED", "IMPORTANT"])'
        },
        removeLabels: {
          type: 'array',
          items: { type: 'string' },
          description: 'Labels to remove (e.g., ["UNREAD", "INBOX"])'
        },
        account: {
          type: 'number',
          default: 1
        }
      },
      required: ['messageId']
    },
    server: 'gmail'
  },
  {
    name: 'gmail_trash_message',
    description: 'Move a Gmail message to trash.',
    inputSchema: {
      type: 'object',
      properties: {
        messageId: {
          type: 'string',
          description: 'The message ID to trash'
        },
        account: {
          type: 'number',
          default: 1
        }
      },
      required: ['messageId']
    },
    server: 'gmail'
  },
  {
    name: 'gmail_list_labels',
    description: 'List all Gmail labels for an account.',
    inputSchema: {
      type: 'object',
      properties: {
        account: {
          type: 'number',
          default: 1
        }
      }
    },
    server: 'gmail'
  },
  // Google Calendar Tools
  {
    name: 'calendar_list_events',
    description: 'List upcoming Google Calendar events.',
    inputSchema: {
      type: 'object',
      properties: {
        maxResults: {
          type: 'number',
          description: 'Maximum events to return (default 10)',
          default: 10
        },
        timeMin: {
          type: 'string',
          description: 'Start time (ISO format, default: now)'
        },
        timeMax: {
          type: 'string',
          description: 'End time (ISO format)'
        },
        calendarId: {
          type: 'string',
          description: 'Calendar ID (default: primary)',
          default: 'primary'
        },
        account: {
          type: 'number',
          default: 1
        }
      }
    },
    server: 'google-calendar'
  },
  {
    name: 'calendar_create_event',
    description: 'Create a new Google Calendar event.',
    inputSchema: {
      type: 'object',
      properties: {
        summary: {
          type: 'string',
          description: 'Event title'
        },
        description: {
          type: 'string',
          description: 'Event description'
        },
        start: {
          type: 'string',
          description: 'Start time (ISO format)'
        },
        end: {
          type: 'string',
          description: 'End time (ISO format)'
        },
        attendees: {
          type: 'array',
          items: { type: 'string' },
          description: 'Email addresses of attendees'
        },
        location: {
          type: 'string',
          description: 'Event location'
        },
        calendarId: {
          type: 'string',
          default: 'primary'
        },
        account: {
          type: 'number',
          default: 1
        }
      },
      required: ['summary', 'start', 'end']
    },
    server: 'google-calendar'
  },
  // Vercel Tools
  {
    name: 'vercel_list_projects',
    description: 'List Vercel projects.',
    inputSchema: {
      type: 'object',
      properties: {
        limit: {
          type: 'number',
          description: 'Number of projects to return',
          default: 20
        }
      }
    },
    server: 'vercel'
  },
  {
    name: 'vercel_get_deployments',
    description: 'Get deployments for a Vercel project.',
    inputSchema: {
      type: 'object',
      properties: {
        projectId: {
          type: 'string',
          description: 'Project ID or name'
        },
        limit: {
          type: 'number',
          default: 10
        }
      },
      required: ['projectId']
    },
    server: 'vercel'
  },
  {
    name: 'vercel_trigger_deployment',
    description: 'Trigger a new deployment for a Vercel project.',
    inputSchema: {
      type: 'object',
      properties: {
        projectId: {
          type: 'string',
          description: 'Project ID or name'
        },
        target: {
          type: 'string',
          enum: ['production', 'preview'],
          default: 'production'
        }
      },
      required: ['projectId']
    },
    server: 'vercel'
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

// Puppeteer executors
async function executePuppeteerNavigate(args) {
  const { url, waitUntil = 'networkidle2' } = args;
  
  if (!url) {
    throw new Error('URL is required');
  }
  
  try {
    const page = await getPage();
    console.log(`[Puppeteer] Navigating to: ${url}`);
    
    await page.goto(url, {
      waitUntil,
      timeout: 30000
    });
    
    const title = await page.title();
    
    return [{
      type: 'text',
      text: JSON.stringify({
        success: true,
        url,
        title,
        message: `Navigated to ${url}`
      })
    }];
  } catch (error) {
    throw new Error(`Navigation failed: ${error.message}`);
  }
}

async function executePuppeteerScreenshot(args) {
  const { fullPage = false, type = 'png' } = args;
  
  try {
    const page = await getPage();
    
    if (!page.url() || page.url() === 'about:blank') {
      throw new Error('No page loaded. Use puppeteer_navigate first.');
    }
    
    console.log(`[Puppeteer] Taking screenshot (fullPage: ${fullPage}, type: ${type})`);
    
    const screenshot = await page.screenshot({
      encoding: 'base64',
      fullPage,
      type
    });
    
    const url = page.url();
    const title = await page.title();
    
    return [{
      type: 'text',
      text: JSON.stringify({
        success: true,
        data: screenshot,
        url,
        title,
        format: type,
        fullPage
      })
    }];
  } catch (error) {
    throw new Error(`Screenshot failed: ${error.message}`);
  }
}

async function executePuppeteerEvaluate(args) {
  const { script } = args;
  
  try {
    const page = await getPage();
    
    if (!page.url() || page.url() === 'about:blank') {
      throw new Error('No page loaded. Use puppeteer_navigate first.');
    }
    
    console.log(`[Puppeteer] Executing script in browser context`);
    
    // Execute script as a raw JS expression (can return a Promise).
    // This intentionally supports passing strings like: "new Promise((resolve)=>{...})"
    const result = await page.evaluate(async (scriptCode) => {
      try {
        // eslint-disable-next-line no-eval
        return await eval(scriptCode);
      } catch (err) {
        return { error: err.message, stack: err.stack };
      }
    }, script);
    
    return [{
      type: 'text',
      text: JSON.stringify({
        success: true,
        result,
        url: page.url()
      })
    }];
  } catch (error) {
    throw new Error(`Script evaluation failed: ${error.message}`);
  }
}

// GitHub helpers
function githubHeaders() {
  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    throw new Error('GITHUB_TOKEN not configured');
  }
  return {
    'Authorization': `token ${token}`,
    'Accept': 'application/vnd.github.v3+json',
    'X-GitHub-Api-Version': '2022-11-28'
  };
}

async function executeGithubCreateRepo(args) {
  const { name, description = '', private: isPrivate = true } = args;
  const headers = githubHeaders();
  const org = process.env.GITHUB_ORG;
  
  const url = org 
    ? `https://api.github.com/orgs/${org}/repos`
    : 'https://api.github.com/user/repos';
  
  try {
    const resp = await axios.post(url, {
      name,
      description,
      private: isPrivate,
      auto_init: true
    }, { headers });
    
    return [{
      type: 'text',
      text: JSON.stringify({
        success: true,
        name: resp.data.name,
        full_name: resp.data.full_name,
        html_url: resp.data.html_url,
        clone_url: resp.data.clone_url
      }, null, 2)
    }];
  } catch (error) {
    if (error.response?.status === 422 && error.response?.data?.errors?.[0]?.message?.includes('already exists')) {
      // Repo already exists, return existing
      const owner = org || (await axios.get('https://api.github.com/user', { headers })).data.login;
      const repoResp = await axios.get(`https://api.github.com/repos/${owner}/${name}`, { headers });
      return [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          name: repoResp.data.name,
          full_name: repoResp.data.full_name,
          html_url: repoResp.data.html_url,
          clone_url: repoResp.data.clone_url,
          already_existed: true
        }, null, 2)
      }];
    }
    throw new Error(`GitHub API error: ${error.response?.data?.message || error.message}`);
  }
}

async function executeGithubPushFiles(args) {
  const { repo, files, message = 'Update from Vibe', branch = 'main' } = args;
  const headers = githubHeaders();
  const org = process.env.GITHUB_ORG;
  
  // Get owner
  let owner = org;
  if (!owner) {
    const userResp = await axios.get('https://api.github.com/user', { headers });
    owner = userResp.data.login;
  }
  
  const repoPath = `https://api.github.com/repos/${owner}/${repo}`;
  
  try {
    // Get latest commit SHA
    let latestSha = null;
    let baseTreeSha = null;
    
    try {
      const refResp = await axios.get(`${repoPath}/git/refs/heads/${branch}`, { headers });
      latestSha = refResp.data.object.sha;
      
      const commitResp = await axios.get(`${repoPath}/git/commits/${latestSha}`, { headers });
      baseTreeSha = commitResp.data.tree.sha;
    } catch (e) {
      // Branch doesn't exist, will create
    }
    
    // Create blobs for each file
    const treeItems = [];
    for (const file of files) {
      const blobResp = await axios.post(`${repoPath}/git/blobs`, {
        content: Buffer.from(file.content).toString('base64'),
        encoding: 'base64'
      }, { headers });
      
      treeItems.push({
        path: file.path,
        mode: '100644',
        type: 'blob',
        sha: blobResp.data.sha
      });
    }
    
    // Create tree
    const treePayload = { tree: treeItems };
    if (baseTreeSha) {
      treePayload.base_tree = baseTreeSha;
    }
    const treeResp = await axios.post(`${repoPath}/git/trees`, treePayload, { headers });
    const newTreeSha = treeResp.data.sha;
    
    // Create commit
    const commitPayload = {
      message,
      tree: newTreeSha,
      parents: latestSha ? [latestSha] : []
    };
    const newCommitResp = await axios.post(`${repoPath}/git/commits`, commitPayload, { headers });
    const newCommitSha = newCommitResp.data.sha;
    
    // Update or create ref
    if (latestSha) {
      await axios.patch(`${repoPath}/git/refs/heads/${branch}`, {
        sha: newCommitSha
      }, { headers });
    } else {
      await axios.post(`${repoPath}/git/refs`, {
        ref: `refs/heads/${branch}`,
        sha: newCommitSha
      }, { headers });
    }
    
    return [{
      type: 'text',
      text: JSON.stringify({
        success: true,
        files_pushed: files.length,
        commit_sha: newCommitSha,
        branch,
        repo: `${owner}/${repo}`
      }, null, 2)
    }];
  } catch (error) {
    throw new Error(`GitHub push failed: ${error.response?.data?.message || error.message}`);
  }
}

// =============================================================================
// GMAIL EXECUTORS
// =============================================================================

// Cache for OAuth2 clients per account
const gmailClients = {};

function getGmailClient(accountNum = 1) {
  const cacheKey = `gmail_${accountNum}`;
  if (gmailClients[cacheKey]) {
    return gmailClients[cacheKey];
  }

  const clientId = process.env.GOOGLE_CLIENT_ID;
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET;
  
  // Get refresh token for the specified account
  let refreshToken;
  if (accountNum === 1) {
    refreshToken = process.env.GOOGLE_REFRESH_TOKEN;
  } else if (accountNum === 2) {
    refreshToken = process.env.GOOGLE_REFRESH_TOKEN_2;
  } else if (accountNum === 3) {
    refreshToken = process.env.GOOGLE_REFRESH_TOKEN_3;
  }

  if (!clientId || !clientSecret || !refreshToken) {
    throw new Error(`Google OAuth not configured for account ${accountNum}. Need GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN${accountNum > 1 ? '_' + accountNum : ''}`);
  }

  const oauth2Client = new google.auth.OAuth2(clientId, clientSecret);
  oauth2Client.setCredentials({ refresh_token: refreshToken });
  
  gmailClients[cacheKey] = google.gmail({ version: 'v1', auth: oauth2Client });
  return gmailClients[cacheKey];
}

function getCalendarClient(accountNum = 1) {
  const cacheKey = `calendar_${accountNum}`;
  if (gmailClients[cacheKey]) {
    return gmailClients[cacheKey];
  }

  const clientId = process.env.GOOGLE_CLIENT_ID;
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET;
  let refreshToken = accountNum === 1 ? process.env.GOOGLE_REFRESH_TOKEN :
                     accountNum === 2 ? process.env.GOOGLE_REFRESH_TOKEN_2 :
                     process.env.GOOGLE_REFRESH_TOKEN_3;

  if (!clientId || !clientSecret || !refreshToken) {
    throw new Error(`Google OAuth not configured for account ${accountNum}`);
  }

  const oauth2Client = new google.auth.OAuth2(clientId, clientSecret);
  oauth2Client.setCredentials({ refresh_token: refreshToken });
  
  gmailClients[cacheKey] = google.calendar({ version: 'v3', auth: oauth2Client });
  return gmailClients[cacheKey];
}

async function executeGmailListMessages(args) {
  const { query = '', maxResults = 10, account = 1 } = args;
  const gmail = getGmailClient(account);

  const response = await gmail.users.messages.list({
    userId: 'me',
    q: query,
    maxResults: Math.min(maxResults, 100)
  });

  const messages = response.data.messages || [];
  
  // Get snippets for each message
  const detailed = await Promise.all(
    messages.slice(0, 20).map(async (msg) => {
      try {
        const detail = await gmail.users.messages.get({
          userId: 'me',
          id: msg.id,
          format: 'metadata',
          metadataHeaders: ['From', 'Subject', 'Date']
        });
        const headers = detail.data.payload?.headers || [];
        return {
          id: msg.id,
          threadId: msg.threadId,
          snippet: detail.data.snippet,
          from: headers.find(h => h.name === 'From')?.value,
          subject: headers.find(h => h.name === 'Subject')?.value,
          date: headers.find(h => h.name === 'Date')?.value,
          labelIds: detail.data.labelIds
        };
      } catch (e) {
        return { id: msg.id, error: e.message };
      }
    })
  );

  return [{ type: 'text', text: JSON.stringify({ messages: detailed, total: response.data.resultSizeEstimate }, null, 2) }];
}

async function executeGmailGetMessage(args) {
  const { messageId, account = 1 } = args;
  const gmail = getGmailClient(account);

  const response = await gmail.users.messages.get({
    userId: 'me',
    id: messageId,
    format: 'full'
  });

  const msg = response.data;
  const headers = msg.payload?.headers || [];
  
  // Extract body
  let body = '';
  function extractBody(part) {
    if (part.body?.data) {
      body += Buffer.from(part.body.data, 'base64').toString('utf-8');
    }
    if (part.parts) {
      part.parts.forEach(extractBody);
    }
  }
  extractBody(msg.payload);

  return [{
    type: 'text',
    text: JSON.stringify({
      id: msg.id,
      threadId: msg.threadId,
      from: headers.find(h => h.name === 'From')?.value,
      to: headers.find(h => h.name === 'To')?.value,
      subject: headers.find(h => h.name === 'Subject')?.value,
      date: headers.find(h => h.name === 'Date')?.value,
      body: body.substring(0, 50000), // Limit body size
      labelIds: msg.labelIds,
      snippet: msg.snippet
    }, null, 2)
  }];
}

async function executeGmailSendMessage(args) {
  const { to, subject, body, cc, bcc, isHtml = false, account = 1 } = args;
  const gmail = getGmailClient(account);

  // Build email
  const boundary = `boundary_${Date.now()}`;
  let email = [
    `To: ${to}`,
    cc ? `Cc: ${cc}` : null,
    bcc ? `Bcc: ${bcc}` : null,
    `Subject: ${subject}`,
    `MIME-Version: 1.0`,
    `Content-Type: ${isHtml ? 'text/html' : 'text/plain'}; charset=utf-8`,
    '',
    body
  ].filter(Boolean).join('\r\n');

  const encodedEmail = Buffer.from(email).toString('base64')
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

  const response = await gmail.users.messages.send({
    userId: 'me',
    requestBody: { raw: encodedEmail }
  });

  return [{
    type: 'text',
    text: JSON.stringify({
      success: true,
      messageId: response.data.id,
      threadId: response.data.threadId
    }, null, 2)
  }];
}

async function executeGmailReplyToMessage(args) {
  const { messageId, body, isHtml = false, account = 1 } = args;
  const gmail = getGmailClient(account);

  // Get original message
  const original = await gmail.users.messages.get({
    userId: 'me',
    id: messageId,
    format: 'metadata',
    metadataHeaders: ['From', 'Subject', 'Message-ID', 'References']
  });

  const headers = original.data.payload?.headers || [];
  const from = headers.find(h => h.name === 'From')?.value;
  const subject = headers.find(h => h.name === 'Subject')?.value || '';
  const messageIdHeader = headers.find(h => h.name === 'Message-ID')?.value;
  const references = headers.find(h => h.name === 'References')?.value || '';

  // Build reply
  let email = [
    `To: ${from}`,
    `Subject: ${subject.startsWith('Re:') ? subject : 'Re: ' + subject}`,
    `In-Reply-To: ${messageIdHeader}`,
    `References: ${references} ${messageIdHeader}`.trim(),
    `MIME-Version: 1.0`,
    `Content-Type: ${isHtml ? 'text/html' : 'text/plain'}; charset=utf-8`,
    '',
    body
  ].join('\r\n');

  const encodedEmail = Buffer.from(email).toString('base64')
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

  const response = await gmail.users.messages.send({
    userId: 'me',
    requestBody: {
      raw: encodedEmail,
      threadId: original.data.threadId
    }
  });

  return [{
    type: 'text',
    text: JSON.stringify({
      success: true,
      messageId: response.data.id,
      threadId: response.data.threadId
    }, null, 2)
  }];
}

async function executeGmailModifyLabels(args) {
  const { messageId, addLabels = [], removeLabels = [], account = 1 } = args;
  const gmail = getGmailClient(account);

  const response = await gmail.users.messages.modify({
    userId: 'me',
    id: messageId,
    requestBody: {
      addLabelIds: addLabels,
      removeLabelIds: removeLabels
    }
  });

  return [{
    type: 'text',
    text: JSON.stringify({
      success: true,
      messageId: response.data.id,
      labelIds: response.data.labelIds
    }, null, 2)
  }];
}

async function executeGmailTrashMessage(args) {
  const { messageId, account = 1 } = args;
  const gmail = getGmailClient(account);

  await gmail.users.messages.trash({
    userId: 'me',
    id: messageId
  });

  return [{ type: 'text', text: JSON.stringify({ success: true, messageId, trashed: true }, null, 2) }];
}

async function executeGmailListLabels(args) {
  const { account = 1 } = args;
  const gmail = getGmailClient(account);

  const response = await gmail.users.labels.list({ userId: 'me' });
  
  return [{
    type: 'text',
    text: JSON.stringify({
      labels: response.data.labels?.map(l => ({
        id: l.id,
        name: l.name,
        type: l.type
      }))
    }, null, 2)
  }];
}

// =============================================================================
// GOOGLE CALENDAR EXECUTORS
// =============================================================================

async function executeCalendarListEvents(args) {
  const { maxResults = 10, timeMin, timeMax, calendarId = 'primary', account = 1 } = args;
  const calendar = getCalendarClient(account);

  const response = await calendar.events.list({
    calendarId,
    timeMin: timeMin || new Date().toISOString(),
    timeMax,
    maxResults,
    singleEvents: true,
    orderBy: 'startTime'
  });

  return [{
    type: 'text',
    text: JSON.stringify({
      events: response.data.items?.map(e => ({
        id: e.id,
        summary: e.summary,
        description: e.description,
        start: e.start?.dateTime || e.start?.date,
        end: e.end?.dateTime || e.end?.date,
        location: e.location,
        attendees: e.attendees?.map(a => a.email),
        status: e.status,
        htmlLink: e.htmlLink
      }))
    }, null, 2)
  }];
}

async function executeCalendarCreateEvent(args) {
  const { summary, description, start, end, attendees = [], location, calendarId = 'primary', account = 1 } = args;
  const calendar = getCalendarClient(account);

  const event = {
    summary,
    description,
    location,
    start: { dateTime: start, timeZone: 'America/New_York' },
    end: { dateTime: end, timeZone: 'America/New_York' },
    attendees: attendees.map(email => ({ email }))
  };

  const response = await calendar.events.insert({
    calendarId,
    requestBody: event,
    sendUpdates: attendees.length > 0 ? 'all' : 'none'
  });

  return [{
    type: 'text',
    text: JSON.stringify({
      success: true,
      eventId: response.data.id,
      htmlLink: response.data.htmlLink,
      summary: response.data.summary
    }, null, 2)
  }];
}

// =============================================================================
// VERCEL EXECUTORS
// =============================================================================

function vercelHeaders() {
  const token = process.env.VERCEL_TOKEN;
  if (!token) {
    throw new Error('VERCEL_TOKEN not configured');
  }
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
}

async function executeVercelListProjects(args) {
  const { limit = 20 } = args;
  const headers = vercelHeaders();
  const teamId = process.env.VERCEL_TEAM_ID;
  
  const url = teamId 
    ? `https://api.vercel.com/v9/projects?teamId=${teamId}&limit=${limit}`
    : `https://api.vercel.com/v9/projects?limit=${limit}`;

  const response = await axios.get(url, { headers });
  
  return [{
    type: 'text',
    text: JSON.stringify({
      projects: response.data.projects?.map(p => ({
        id: p.id,
        name: p.name,
        framework: p.framework,
        latestDeployment: p.latestDeployments?.[0]?.url
      }))
    }, null, 2)
  }];
}

async function executeVercelGetDeployments(args) {
  const { projectId, limit = 10 } = args;
  const headers = vercelHeaders();
  const teamId = process.env.VERCEL_TEAM_ID;
  
  let url = `https://api.vercel.com/v6/deployments?projectId=${projectId}&limit=${limit}`;
  if (teamId) url += `&teamId=${teamId}`;

  const response = await axios.get(url, { headers });
  
  return [{
    type: 'text',
    text: JSON.stringify({
      deployments: response.data.deployments?.map(d => ({
        id: d.uid,
        url: d.url,
        state: d.state,
        target: d.target,
        createdAt: d.createdAt,
        ready: d.ready
      }))
    }, null, 2)
  }];
}

async function executeVercelTriggerDeployment(args) {
  const { projectId, target = 'production' } = args;
  const headers = vercelHeaders();
  const teamId = process.env.VERCEL_TEAM_ID;
  
  // Get project to find the git repo
  let projectUrl = `https://api.vercel.com/v9/projects/${projectId}`;
  if (teamId) projectUrl += `?teamId=${teamId}`;
  
  const projectResp = await axios.get(projectUrl, { headers });
  const project = projectResp.data;
  
  // Trigger deployment via deploy hook or API
  let deployUrl = `https://api.vercel.com/v13/deployments`;
  if (teamId) deployUrl += `?teamId=${teamId}`;
  
  const response = await axios.post(deployUrl, {
    name: project.name,
    target,
    gitSource: project.link ? {
      type: project.link.type,
      repoId: project.link.repoId,
      ref: project.link.productionBranch || 'main'
    } : undefined
  }, { headers });
  
  return [{
    type: 'text',
    text: JSON.stringify({
      success: true,
      deploymentId: response.data.id,
      url: response.data.url,
      state: response.data.state
    }, null, 2)
  }];
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
  'recraft_generate_image': executeRecraftGenerateImage,
  'puppeteer_navigate': executePuppeteerNavigate,
  'puppeteer_screenshot': executePuppeteerScreenshot,
  'puppeteer_evaluate': executePuppeteerEvaluate,
  'github_create_repo': executeGithubCreateRepo,
  'github_push_files': executeGithubPushFiles,
  // Gmail
  'gmail_list_messages': executeGmailListMessages,
  'gmail_get_message': executeGmailGetMessage,
  'gmail_send_message': executeGmailSendMessage,
  'gmail_reply_to_message': executeGmailReplyToMessage,
  'gmail_modify_labels': executeGmailModifyLabels,
  'gmail_trash_message': executeGmailTrashMessage,
  'gmail_list_labels': executeGmailListLabels,
  // Calendar
  'calendar_list_events': executeCalendarListEvents,
  'calendar_create_event': executeCalendarCreateEvent,
  // Vercel
  'vercel_list_projects': executeVercelListProjects,
  'vercel_get_deployments': executeVercelGetDeployments,
  'vercel_trigger_deployment': executeVercelTriggerDeployment
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
  console.log(`  BRAVE_API_KEY:      ${process.env.BRAVE_API_KEY ? '✓ configured' : '✗ NOT CONFIGURED'}`);
  console.log(`  NOTION_API_KEY:     ${process.env.NOTION_API_KEY ? '✓ configured' : '✗ NOT CONFIGURED'}`);
  console.log(`  RECRAFT_API_KEY:    ${process.env.RECRAFT_API_KEY ? '✓ configured' : '✗ NOT CONFIGURED'}`);
  console.log(`  GITHUB_TOKEN:       ${process.env.GITHUB_TOKEN ? '✓ configured' : '✗ NOT CONFIGURED'}`);
  console.log(`  GITHUB_ORG:         ${process.env.GITHUB_ORG || '(using personal account)'}`);
  console.log(`  VERCEL_TOKEN:       ${process.env.VERCEL_TOKEN ? '✓ configured' : '✗ NOT CONFIGURED'}`);
  console.log(`  VERCEL_TEAM_ID:     ${process.env.VERCEL_TEAM_ID || '(using personal account)'}`);
  console.log(`\nGoogle Services:`);
  console.log(`  GOOGLE_CLIENT_ID:   ${process.env.GOOGLE_CLIENT_ID ? '✓ configured' : '✗ NOT CONFIGURED'}`);
  console.log(`  GOOGLE_CLIENT_SECRET: ${process.env.GOOGLE_CLIENT_SECRET ? '✓ configured' : '✗ NOT CONFIGURED'}`);
  console.log(`  Account 1 (Gmail):  ${process.env.GOOGLE_REFRESH_TOKEN ? '✓ configured' : '✗ NOT CONFIGURED'}`);
  console.log(`  Account 2 (Gmail):  ${process.env.GOOGLE_REFRESH_TOKEN_2 ? '✓ configured' : '✗ NOT CONFIGURED'}`);
  console.log(`  Account 3 (Gmail):  ${process.env.GOOGLE_REFRESH_TOKEN_3 ? '✓ configured' : '✗ NOT CONFIGURED'}`);
  console.log(`\n${'='.repeat(60)}\n`);
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('Shutting down MCP HTTP Bridge...');
  if (browser) {
    await browser.close();
    console.log('[Puppeteer] Browser closed');
  }
  process.exit(0);
});

process.on('SIGINT', async () => {
  console.log('Shutting down MCP HTTP Bridge...');
  if (browser) {
    await browser.close();
    console.log('[Puppeteer] Browser closed');
  }
  process.exit(0);
});

