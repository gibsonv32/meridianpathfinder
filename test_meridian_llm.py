#!/usr/bin/env python3
"""Test MERIDIAN LLM configuration and connection."""

import sys
import yaml
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from meridian.llm.providers import get_provider


def test_meridian_config():
    """Test the MERIDIAN LLM configuration from meridian.yaml."""
    print("Testing MERIDIAN LLM configuration...")
    print("-" * 50)
    
    # Load configuration
    config_path = Path("meridian.yaml")
    if not config_path.exists():
        print("✗ meridian.yaml not found!")
        return False
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    llm_config = config.get("llm", {})
    print(f"Provider: {llm_config.get('provider')}")
    print(f"Model: {llm_config.get('model')}")
    print(f"Base URL: {llm_config.get('base_url')}")
    print(f"Temperature: {llm_config.get('temperature')}")
    print()
    
    # Get provider
    try:
        provider = get_provider(config, Path.cwd())
        print(f"✓ Provider initialized: {provider.__class__.__name__}")
    except Exception as e:
        print(f"✗ Failed to initialize provider: {e}")
        return False
    
    # Test connection
    print("\nTesting connection...")
    try:
        if hasattr(provider, 'test_connection'):
            if provider.test_connection():
                print("✓ Connection successful!")
            else:
                print("✗ Connection failed!")
                print("\nTroubleshooting steps:")
                print("1. Check if the Spark server is running:")
                print("   curl http://127.0.0.1:30000/v1/models")
                print("2. Verify the model is loaded")
                print("3. Check firewall/network settings")
                return False
        else:
            # For wrapped providers, try a simple completion
            response = provider.complete("ping", max_tokens=5)
            print(f"✓ Connection test successful! Response: {response}")
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        return False
    
    # Test simple completion
    print("\nTesting simple completion...")
    try:
        response = provider.complete(
            "What is the capital of France? Answer in one word.",
            max_tokens=20
        )
        print(f"Response: {response}")
        print("✓ Completion successful!")
    except Exception as e:
        print(f"✗ Completion failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("Configuration test completed!")
    return True


if __name__ == "__main__":
    success = test_meridian_config()
    sys.exit(0 if success else 1)