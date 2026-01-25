#!/usr/bin/env python3
"""
Simple mock OpenAI API server using only standard library.
For testing MERIDIAN's OpenAI provider locally.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time

class OpenAIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/v1/models':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                "object": "list",
                "data": [{
                    "id": "openai/gpt-oss-120b",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "meridian"
                }]
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/v1/chat/completions':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body) if body else {}
            
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
            elif "csv" in last_message.lower() and ("delimiter" in last_message.lower() or "sep" in last_message.lower() or "schema" in last_message.lower()):
                # For CSV delimiter issues - return proper JSON fix with semicolon
                response_text = '{"sep": ";", "encoding": "utf-8", "skiprows": null, "header": 0}'
            elif "feature" in last_message.lower() and "error" in last_message.lower():
                # For feature engineering errors
                response_text = "fillna(0)"
            else:
                response_text = f"Mock response to: {last_message[:50]}"
            
            # Support JSON mode if requested
            response_format = data.get('response_format', {})
            if response_format.get('type') == 'json_object' and '{' not in response_text:
                response_text = f'{{"response": "{response_text}"}}'
            
            response = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": data.get('model', 'openai/gpt-oss-120b'),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 10,
                    "total_tokens": 20
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
        """Suppress request logging for cleaner output."""
        pass

def run_server():
    """Run the mock server."""
    server_address = ('127.0.0.1', 30000)
    httpd = HTTPServer(server_address, OpenAIHandler)
    print("Mock gpt-oss-120b server running on http://127.0.0.1:30000")
    print("This simulates the OpenAI API for testing.")
    print("Press Ctrl+C to stop the server.")
    print("-" * 50)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        httpd.server_close()

if __name__ == '__main__':
    run_server()