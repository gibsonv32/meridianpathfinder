#!/usr/bin/env python3
"""
Mock OpenAI API server for testing MERIDIAN's OpenAI provider.
This simulates the gpt-oss-120b server for local testing.
"""

from flask import Flask, request, jsonify
import time

app = Flask(__name__)

@app.route('/v1/models', methods=['GET'])
def list_models():
    """List available models."""
    return jsonify({
        "object": "list",
        "data": [
            {
                "id": "openai/gpt-oss-120b",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "meridian"
            }
        ]
    })

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """Handle chat completion requests."""
    data = request.json
    
    # Extract messages
    messages = data.get('messages', [])
    last_message = messages[-1]['content'] if messages else "Hello"
    
    # Simple mock responses
    if "ping" in last_message.lower():
        response_text = "pong"
    elif "capital of france" in last_message.lower():
        response_text = "Paris"
    elif "2+2" in last_message.lower() or "2 + 2" in last_message.lower():
        response_text = "4"
    elif "multiply" in last_message.lower() and "5" in last_message and "3" in last_message:
        response_text = '{"answer": 15, "explanation": "5 multiplied by 3 equals 15"}'
    else:
        response_text = f"Mock response to: {last_message[:50]}"
    
    # Support JSON mode if requested
    response_format = data.get('response_format', {})
    if response_format.get('type') == 'json_object' and '{' not in response_text:
        response_text = f'{{"response": "{response_text}"}}'
    
    return jsonify({
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": data.get('model', 'openai/gpt-oss-120b'),
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 10,
            "total_tokens": 20
        }
    })

if __name__ == '__main__':
    print("Starting mock gpt-oss-120b server on http://127.0.0.1:30000")
    print("This is for testing MERIDIAN's OpenAI provider locally.")
    print("Press Ctrl+C to stop the server.")
    print("-" * 50)
    app.run(host='127.0.0.1', port=30000, debug=False)