#!/bin/bash
echo "==================================================="
echo "FAZ CODE DEPLOYMENT CONFIGURATION CHECK"
echo "==================================================="
echo ""
echo "Checking on droplet..."
echo ""

ssh root@138.197.93.24 << 'ENDSSH'
source /opt/nicole/.env

echo "GitHub Configuration:"
echo "---------------------"
if [ -n "$GITHUB_TOKEN" ]; then
  echo "✓ GITHUB_TOKEN: Set (${#GITHUB_TOKEN} chars)"
else
  echo "✗ GITHUB_TOKEN: NOT SET"
fi

if [ -n "$GITHUB_ORG" ]; then
  echo "✓ GITHUB_ORG: $GITHUB_ORG"
else
  echo "✗ GITHUB_ORG: NOT SET"
fi

echo ""
echo "Vercel Configuration:"
echo "---------------------"
if [ -n "$VERCEL_TOKEN" ]; then
  echo "✓ VERCEL_TOKEN: Set (${#VERCEL_TOKEN} chars)"
else
  echo "✗ VERCEL_TOKEN: NOT SET"
fi

if [ -n "$VERCEL_TEAM_ID" ]; then
  echo "✓ VERCEL_TEAM_ID: $VERCEL_TEAM_ID"
else
  echo "○ VERCEL_TEAM_ID: Not set (optional)"
fi

echo ""
echo "==================================================="
echo "TESTING API CONNECTIVITY"
echo "==================================================="
echo ""

# Test GitHub API
if [ -n "$GITHUB_TOKEN" ]; then
  echo "Testing GitHub API..."
  GITHUB_RESPONSE=$(curl -s -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/user)
  if echo "$GITHUB_RESPONSE" | grep -q "login"; then
    USERNAME=$(echo "$GITHUB_RESPONSE" | grep -o '"login":"[^"]*' | cut -d'"' -f4)
    echo "✓ GitHub API: Connected as $USERNAME"
  else
    echo "✗ GitHub API: Failed - $(echo "$GITHUB_RESPONSE" | head -1)"
  fi
else
  echo "○ GitHub API: Skipped (no token)"
fi

echo ""

# Test Vercel API
if [ -n "$VERCEL_TOKEN" ]; then
  echo "Testing Vercel API..."
  VERCEL_RESPONSE=$(curl -s -H "Authorization: Bearer $VERCEL_TOKEN" https://api.vercel.com/v2/user)
  if echo "$VERCEL_RESPONSE" | grep -q "username"; then
    VERCEL_USER=$(echo "$VERCEL_RESPONSE" | grep -o '"username":"[^"]*' | cut -d'"' -f4)
    echo "✓ Vercel API: Connected as $VERCEL_USER"
  else
    echo "✗ Vercel API: Failed - $(echo "$VERCEL_RESPONSE" | head -1)"
  fi
else
  echo "○ Vercel API: Skipped (no token)"
fi

ENDSSH
