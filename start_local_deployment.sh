#!/bin/bash
# Start MERIDIAN local deployment for testing

echo "Starting MERIDIAN Local Deployment..."
echo "====================================="

# Terminal 1: Model Server
echo "1. Starting mock model server on port 30000..."
python3 simple_test_server.py &
MODEL_PID=$!
sleep 2

# Terminal 2: API Server
echo "2. Starting API server on port 8000..."
python3 -m meridian.api.server &
API_PID=$!
sleep 3

# Test the deployment
echo "3. Testing deployment..."
echo "-----------------------------------"
curl -s http://localhost:8000/health | python3 -m json.tool
echo ""

echo "====================================="
echo "Deployment running!"
echo "Model Server PID: $MODEL_PID"
echo "API Server PID: $API_PID"
echo ""
echo "Access the API at: http://localhost:8000"
echo "WebSocket at: ws://localhost:8000/ws"
echo ""
echo "To stop: kill $MODEL_PID $API_PID"
echo "====================================="

# Keep running
wait