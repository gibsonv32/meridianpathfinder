#!/usr/bin/env python3
"""
Simple Mock SGLang Server for Development/Testing
Provides an OpenAI-compatible API endpoint on port 30000
Uses only Python standard library
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time
import uuid

class MockSGLangHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/v1/models':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                "object": "list",
                "data": [
                    {
                        "id": "gpt-oss-120b",
                        "object": "model",
                        "created": 1686935002,
                        "owned_by": "meridian"
                    }
                ]
            }
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {"status": "healthy", "service": "mock-sglang"}
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
        except:
            data = {}
        
        if self.path == '/v1/chat/completions':
            messages = data.get('messages', [])
            last_message = messages[-1]['content'] if messages else "Hello"
            
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
                            "content": f"[Mock Response] Processing: '{last_message[:50]}...'. This is a mock response for testing."
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
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        elif self.path == '/v1/completions':
            prompt = data.get('prompt', 'Hello')
            
            response = {
                "id": f"cmpl-{uuid.uuid4().hex[:8]}",
                "object": "text_completion",
                "created": int(time.time()),
                "model": "gpt-oss-120b",
                "choices": [
                    {
                        "text": f"[Mock] Completing: '{prompt[:50]}...'",
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
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Override to reduce log verbosity"""
        pass

if __name__ == '__main__':
    print("=" * 60)
    print("Starting Mock SGLang Server")
    print("=" * 60)
    print("⚠️  This is a MOCK server for development/testing")
    print("It provides placeholder responses, not actual AI completions")
    print("")
    print("To use real GPT-OSS-120B, you need:")
    print("1. Model files at /mnt/spark-data3/models/gpt-oss-120b")
    print("2. SGLang installed with all dependencies")
    print("=" * 60)
    print(f"Mock server running on http://127.0.0.1:30000")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    server = HTTPServer(('127.0.0.1', 30000), MockSGLangHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down mock server...")
        server.shutdown()