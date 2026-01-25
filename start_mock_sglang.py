#!/usr/bin/env python3
"""
Mock SGLang Server for Development/Testing
Provides an OpenAI-compatible API endpoint on port 30000
"""

from flask import Flask, request, jsonify
import time
import uuid

app = Flask(__name__)

@app.route('/v1/models', methods=['GET'])
def list_models():
    """List available models"""
    return jsonify({
        "object": "list",
        "data": [
            {
                "id": "gpt-oss-120b",
                "object": "model",
                "created": 1686935002,
                "owned_by": "meridian"
            }
        ]
    })

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """Handle chat completion requests"""
    data = request.json
    
    # Extract the messages
    messages = data.get('messages', [])
    last_message = messages[-1]['content'] if messages else "Hello"
    
    # Create a mock response
    response = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "gpt-oss-120b",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"[Mock Response] I received your message: '{last_message[:100]}...'. This is a mock response for testing. The real SGLang server would provide actual AI responses here."
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        }
    }
    
    return jsonify(response)

@app.route('/v1/completions', methods=['POST'])
def completions():
    """Handle completion requests"""
    data = request.json
    prompt = data.get('prompt', 'Hello')
    
    response = {
        "id": f"cmpl-{uuid.uuid4().hex[:8]}",
        "object": "text_completion",
        "created": int(time.time()),
        "model": "gpt-oss-120b",
        "choices": [
            {
                "text": f"[Mock Response] Completing: '{prompt[:100]}...' - This is a mock response.",
                "index": 0,
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        }
    }
    
    return jsonify(response)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "mock-sglang"})

if __name__ == '__main__':
    print("=" * 60)
    print("Starting Mock SGLang Server")
    print("=" * 60)
    print("This is a MOCK server for development/testing")
    print("It will provide placeholder responses, not actual AI completions")
    print("To use real GPT-OSS-120B, you need:")
    print("1. Model files at /mnt/spark-data3/models/gpt-oss-120b")
    print("2. SGLang installed with dependencies")
    print("=" * 60)
    print(f"Server running on http://0.0.0.0:30000")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=30000, debug=False)