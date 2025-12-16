#!/bin/bash
# Simple Docker Startup Script with Reddit Access Token Automation

echo "🚀 Starting Social Media Agent with Reddit Auto-Refresh"
echo "====================================================="

# Test Reddit connection and refresh token if needed
echo "🔧 Testing Reddit connection..."
python3 -c "
from reddit_token_refresh import RedditTokenRefresh
import os

# Check if we have the required tokens
if not all([os.getenv('REDDIT_CLIENT_ID'), os.getenv('REDDIT_CLIENT_SECRET'), os.getenv('REDDIT_REFRESH_TOKEN')]):
    print('❌ Missing Reddit credentials. Please set environment variables.')
    exit(1)

service = RedditTokenRefresh()
if service.test_connection():
    print('✅ Reddit integration ready!')
else:
    print('❌ Reddit integration failed')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo "🚀 Starting main application..."
    python3 main.py
else
    echo "❌ Failed to initialize Reddit integration"
    exit 1
fi