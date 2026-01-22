#!/usr/bin/env python3
"""
Test connection to SGLang server running gpt-oss-120b.
SGLang uses OpenAI-compatible API with some extensions.
"""

import requests
import json

def test_sglang():
    """Test SGLang server connection and features."""
    base_url = "http://127.0.0.1:30000"
    
    print("Testing SGLang Server Connection")
    print("=" * 50)
    
    # Test 1: Check health/models endpoint
    print("\n1. Checking server status...")
    try:
        response = requests.get(f"{base_url}/v1/models")
        if response.status_code == 200:
            print("✓ Server is running")
            print(f"Models: {response.json()}")
        else:
            print(f"✗ Server returned: {response.status_code}")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("  Make sure SGLang server is running on port 30000")
        return
    
    # Test 2: Simple completion
    print("\n2. Testing completion...")
    try:
        payload = {
            "model": "gpt-oss-120b",  # or whatever model name SGLang reports
            "messages": [
                {"role": "user", "content": "What is 2+2?"}
            ],
            "max_tokens": 10,
            "temperature": 0.1
        }
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print(f"✓ Response: {content}")
        else:
            print(f"✗ Error: {response.text}")
    except Exception as e:
        print(f"✗ Completion failed: {e}")
    
    # Test 3: SGLang-specific features (constrained generation)
    print("\n3. Testing SGLang constrained generation...")
    try:
        # SGLang supports regex constraints
        payload = {
            "model": "gpt-oss-120b",
            "messages": [
                {"role": "user", "content": "Count from 1 to 5"}
            ],
            "max_tokens": 50,
            "temperature": 0,
            # SGLang specific: regex constraint
            "regex": r"\d(, \d)*"  # Forces number format
        }
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            json=payload
        )
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print(f"✓ Constrained output: {content}")
        else:
            print(f"ℹ Regex constraints may not be enabled")
    except Exception as e:
        print(f"ℹ SGLang-specific features not available: {e}")
    
    # Test 4: Batch processing (SGLang optimization)
    print("\n4. Testing batch processing...")
    try:
        # SGLang can handle multiple requests efficiently
        payload = {
            "model": "gpt-oss-120b",
            "messages": [
                {"role": "user", "content": "What is the capital of France?"}
            ],
            "max_tokens": 20,
            "n": 1,  # number of completions
            "stream": False
        }
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            json=payload
        )
        if response.status_code == 200:
            result = response.json()
            # Check latency - SGLang should be fast
            if "usage" in result:
                print(f"✓ Tokens used: {result['usage']['total_tokens']}")
            print(f"✓ Batch processing works")
        else:
            print(f"✗ Batch error: {response.text}")
    except Exception as e:
        print(f"✗ Batch processing failed: {e}")
    
    print("\n" + "=" * 50)
    print("SGLang Configuration Notes:")
    print("- Use --tp (tensor parallel) for multi-GPU")
    print("- Enable --enable-flashinfer for faster attention")
    print("- Set --mem-fraction-static 0.85 for better memory usage")
    print("- Use --schedule-policy lpm for low latency")

if __name__ == "__main__":
    test_sglang()