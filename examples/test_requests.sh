#!/bin/bash

# TG200 FastAPI Test Script
# Set your bearer token
TOKEN="your-secret-token-here"

echo "=== TG200 FastAPI Test Requests ==="
echo ""

# 1. Test root endpoint
echo "1. Testing root endpoint..."
curl -s http://localhost:8000/ | jq .
echo ""

# 2. Test status endpoint (with auth)
echo "2. Testing status endpoint..."
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/status | jq .
echo ""

# 3. Test send SMS endpoint (with auth)
echo "3. Testing send SMS endpoint..."
curl -s -X POST http://localhost:8000/sms/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @examples/send_sms.json | jq .
echo ""

# 4. Test incoming webhook
echo "4. Testing incoming webhook..."
curl -s -X POST http://localhost:8000/webhook/incoming \
  -H "Content-Type: application/json" \
  -d @examples/incoming_webhook.json | jq .
echo ""

echo "=== Tests completed ==="
