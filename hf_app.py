import socket

# Force IPv4 to fix Hugging Face Docker IPv6 blackholing (Fixes Telegram and WebSocket timeouts)
old_getaddrinfo = socket.getaddrinfo
def new_getaddrinfo(*args, **kwargs):
    responses = old_getaddrinfo(*args, **kwargs)
    return [response for response in responses if response[0] == socket.AF_INET]
socket.getaddrinfo = new_getaddrinfo

import threading
import http.server
import socketserver
import asyncio
import os
from main import main as start_bot

# 1. Tiny Web Server to keep Hugging Face alive
PORT = 7860
class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("<html><body><h1>🚀 Antigravity Bot is Running!</h1><p>Monitoring markets 24/7...</p></body></html>".encode('utf-8'))

def run_web_server():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Heartbeat server running on port {PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    # Start Web Server in a background thread
    threading.Thread(target=run_web_server, daemon=True).start()
    
    # Start the Trading Bot
    print("Starting Trading Engine...")
    asyncio.run(start_bot())
