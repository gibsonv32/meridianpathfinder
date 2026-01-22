#!/usr/bin/env python3
"""Test OpenAI provider connection to local gpt-oss-120b model."""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from meridian.llm.providers import OpenAIProvider


def test_connection():
    """Test the connection to the local gpt-oss-120b model."""
    print("Testing connection to gpt-oss-120b on Spark...")
    print("-" * 50)
    
    # Initialize provider with local settings
    provider = OpenAIProvider(
        api_key="not-needed",
        base_url="http://127.0.0.1:30000/v1",
        model="openai/gpt-oss-120b",
        temperature=0.3
    )
    
    # Test 1: Basic connection test
    print("1. Testing basic connection...")
    if provider.test_connection():
        print("   ✓ Connection successful!")
    else:
        print("   ✗ Connection failed!")
        print("   Make sure the Spark server is running on port 30000")
        return False
    
    # Test 2: Simple completion
    print("\n2. Testing simple completion...")
    try:
        response = provider.complete(
            prompt="What is 2+2? Answer with just the number.",
            max_tokens=10
        )
        print(f"   Response: {response}")
        print("   ✓ Completion successful!")
    except Exception as e:
        print(f"   ✗ Completion failed: {e}")
        return False
    
    # Test 3: Completion with system message
    print("\n3. Testing completion with system message...")
    try:
        response = provider.complete(
            prompt="Hello!",
            system="You are a helpful assistant. Respond briefly.",
            max_tokens=50
        )
        print(f"   Response: {response}")
        print("   ✓ System message completion successful!")
    except Exception as e:
        print(f"   ✗ System message completion failed: {e}")
        return False
    
    # Test 4: Structured output
    print("\n4. Testing structured output...")
    try:
        from pydantic import BaseModel
        
        class SimpleResponse(BaseModel):
            answer: int
            explanation: str
        
        response = provider.complete_structured(
            prompt="What is 5 multiplied by 3?",
            schema=SimpleResponse
        )
        print(f"   Response: answer={response.answer}, explanation='{response.explanation}'")
        print("   ✓ Structured output successful!")
    except Exception as e:
        print(f"   ✗ Structured output failed: {e}")
        print("   Note: Some local models may not support structured output")
    
    print("\n" + "=" * 50)
    print("All basic tests completed successfully!")
    return True


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)