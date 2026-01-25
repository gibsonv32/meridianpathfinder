#!/usr/bin/env python3
"""
Test MERIDIAN deployment as it would run on Spark/DGX.
Simulates the full stack locally.
"""

import os
import sys
import time
import subprocess
import requests
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

def test_deployment_stack():
    """Test the deployment stack components."""
    print("=" * 60)
    print("MERIDIAN SPARK DEPLOYMENT TEST")
    print("=" * 60)
    print()
    
    # Test 1: API Server
    print("1. Testing API Server...")
    print("-" * 40)
    try:
        # Check if API server is running
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            print("✓ API Server is running")
            print(f"  Response: {response.json()}")
        else:
            print("✗ API Server not responding correctly")
    except requests.exceptions.RequestException:
        print("✗ API Server not running")
        print("  To start: python -m meridian.api.server")
    print()
    
    # Test 2: Model Server
    print("2. Testing Model Server (gpt-oss-120b)...")
    print("-" * 40)
    try:
        response = requests.get("http://localhost:30000/v1/models", timeout=2)
        if response.status_code == 200:
            print("✓ Model server is running")
            models = response.json().get("data", [])
            for model in models:
                print(f"  - {model.get('id')}")
        else:
            print("✗ Model server not responding")
    except requests.exceptions.RequestException:
        print("✗ Model server not running on port 30000")
        print("  To start mock: python3 simple_test_server.py")
    print()
    
    # Test 3: Mode Execution
    print("3. Testing Mode Execution...")
    print("-" * 40)
    try:
        from meridian.core.state import MeridianProject
        from meridian.config import load_config
        
        config = load_config(Path("meridian.yaml"))
        project = MeridianProject.from_config(config)
        
        # Test a simple mode
        mode_0_result = project.execute_mode(
            0, 
            user_input="Test deployment",
            context={"deployment_test": True}
        )
        print(f"✓ Mode 0 executed: {mode_0_result.status}")
    except Exception as e:
        print(f"✗ Mode execution failed: {e}")
    print()
    
    # Test 4: WebSocket Support
    print("4. Testing WebSocket Support...")
    print("-" * 40)
    try:
        import websocket
        ws = websocket.create_connection("ws://localhost:8000/ws")
        ws.send('{"type": "ping"}')
        result = ws.recv()
        ws.close()
        print(f"✓ WebSocket connection successful")
    except:
        print("✗ WebSocket not available (API server may not be running)")
    print()
    
    # Deployment Recommendations
    print("=" * 60)
    print("DEPLOYMENT RECOMMENDATION")
    print("=" * 60)
    print()
    print("Based on your setup, here's the optimal deployment strategy:")
    print()
    print("1. FOR DGX/SPARK PRODUCTION (Recommended):")
    print("   - Use NVIDIA Base Command for job scheduling")
    print("   - Deploy model servers with vLLM on GPUs")
    print("   - Run API server with uvicorn")
    print("   - Use the existing FastAPI + WebSocket architecture")
    print()
    print("2. FOR LOCAL TESTING:")
    print("   - Use the mock server (simple_test_server.py)")
    print("   - Run API server locally")
    print("   - Test with curl or the web interface")
    print()
    print("3. QUICK START COMMANDS:")
    print("   # Terminal 1: Start mock model server")
    print("   python3 simple_test_server.py")
    print()
    print("   # Terminal 2: Start API server")
    print("   python -m meridian.api.server")
    print()
    print("   # Terminal 3: Test the deployment")
    print("   curl http://localhost:8000/health")
    print("   curl -X POST http://localhost:8000/api/execute/0 \\")
    print('        -H "Content-Type: application/json" \\')
    print('        -d \'{"input": "Test message"}\'')


if __name__ == "__main__":
    test_deployment_stack()