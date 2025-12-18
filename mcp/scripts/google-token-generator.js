#!/usr/bin/env node
/**
 * Google OAuth Token Generator for Nicole MCP
 * 
 * This script helps you generate refresh tokens for Gmail/Calendar access.
 * 
 * Prerequisites:
 * 1. Go to https://console.cloud.google.com/
 * 2. Create a project (or select existing)
 * 3. Enable Gmail API and Google Calendar API
 * 4. Go to APIs & Services > Credentials
 * 5. Create OAuth 2.0 Client ID (Desktop app type)
 * 6. Download the client_secret.json file
 * 
 * Usage:
 *   node google-token-generator.js path/to/client_secret.json
 * 
 * The script will:
 * 1. Open a browser for you to authorize
 * 2. Print the refresh token to use in your .env file
 */

const { google } = require('googleapis');
const http = require('http');
const url = require('url');
const fs = require('fs');
const open = require('open');

const SCOPES = [
  'https://www.googleapis.com/auth/gmail.readonly',
  'https://www.googleapis.com/auth/gmail.send',
  'https://www.googleapis.com/auth/gmail.modify',
  'https://www.googleapis.com/auth/gmail.labels',
  'https://www.googleapis.com/auth/calendar.readonly',
  'https://www.googleapis.com/auth/calendar.events'
];

async function main() {
  const credentialsPath = process.argv[2];
  
  if (!credentialsPath) {
    console.log(`
╔════════════════════════════════════════════════════════════════╗
║       Google OAuth Token Generator for Nicole MCP              ║
╚════════════════════════════════════════════════════════════════╝

Usage: node google-token-generator.js <path-to-client_secret.json>

Steps to get client_secret.json:
1. Go to https://console.cloud.google.com/
2. Create a project (or select existing)
3. Enable Gmail API and Google Calendar API
4. Go to APIs & Services > Credentials
5. Create OAuth 2.0 Client ID (Desktop app type)
6. Download the JSON file
`);
    process.exit(1);
  }

  // Load credentials
  let credentials;
  try {
    const content = fs.readFileSync(credentialsPath, 'utf-8');
    credentials = JSON.parse(content);
  } catch (err) {
    console.error(`Error reading credentials file: ${err.message}`);
    process.exit(1);
  }

  const { client_id, client_secret } = credentials.installed || credentials.web || {};
  
  if (!client_id || !client_secret) {
    console.error('Invalid credentials file format');
    process.exit(1);
  }

  const oauth2Client = new google.auth.OAuth2(
    client_id,
    client_secret,
    'http://localhost:3000/callback'
  );

  // Generate auth URL
  const authUrl = oauth2Client.generateAuthUrl({
    access_type: 'offline',
    scope: SCOPES,
    prompt: 'consent' // Force consent to get refresh token
  });

  console.log(`
╔════════════════════════════════════════════════════════════════╗
║                   Opening browser for authorization            ║
╚════════════════════════════════════════════════════════════════╝

If the browser doesn't open, visit this URL:
${authUrl}

Waiting for authorization...
`);

  // Start local server to receive callback
  return new Promise((resolve, reject) => {
    const server = http.createServer(async (req, res) => {
      const parsedUrl = url.parse(req.url, true);
      
      if (parsedUrl.pathname === '/callback') {
        const code = parsedUrl.query.code;
        
        if (code) {
          try {
            const { tokens } = await oauth2Client.getToken(code);
            
            res.writeHead(200, { 'Content-Type': 'text/html' });
            res.end(`
              <html>
                <body style="font-family: system-ui; padding: 40px; text-align: center;">
                  <h1>✅ Authorization Successful!</h1>
                  <p>You can close this window and return to the terminal.</p>
                </body>
              </html>
            `);

            console.log(`
╔════════════════════════════════════════════════════════════════╗
║                   ✅ Authorization Successful!                 ║
╚════════════════════════════════════════════════════════════════╝

Add this to your .env file:

GOOGLE_CLIENT_ID=${client_id}
GOOGLE_CLIENT_SECRET=${client_secret}
GOOGLE_REFRESH_TOKEN=${tokens.refresh_token}

For additional accounts, run this script again and use:
GOOGLE_REFRESH_TOKEN_2=<token>
GOOGLE_REFRESH_TOKEN_3=<token>
`);

            server.close();
            resolve(tokens);
          } catch (err) {
            res.writeHead(500, { 'Content-Type': 'text/plain' });
            res.end(`Error: ${err.message}`);
            reject(err);
          }
        } else {
          res.writeHead(400, { 'Content-Type': 'text/plain' });
          res.end('No authorization code received');
        }
      }
    });

    server.listen(3000, () => {
      // Try to open browser
      open(authUrl).catch(() => {
        console.log('Could not open browser automatically. Please visit the URL above.');
      });
    });
  });
}

main().catch(console.error);

