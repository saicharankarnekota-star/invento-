"""INVENTO AI Application Root Entrypoint.
Delegates to backend/app.py to run the full stack server.
"""
import sys
import os
import socket
from werkzeug.serving import WSGIRequestHandler

class FriendlyWSGIRequestHandler(WSGIRequestHandler):
    """Intercepts TLS/HTTPS handshakes on plain HTTP dev ports with a friendly explanation."""
    def handle_one_request(self):
        try:
            peek = self.connection.recv(1, socket.MSG_PEEK)
            if peek == b"\x16":
                self.close_connection = True
                port = getattr(self.server, "server_port", 5001)
                print(f"\n[⚠️ Notice] HTTPS request received on plain HTTP port {port}.")
                print(f"👉 Please open HTTP in your browser: http://127.0.0.1:{port}/\n")
                try:
                    msg = (
                        f"HTTP/1.1 400 Bad Request\r\n"
                        f"Content-Type: text/html; charset=utf-8\r\n"
                        f"Connection: close\r\n\r\n"
                        f"<!DOCTYPE html><html><head><title>Use HTTP</title></head>"
                        f"<body style='font-family:sans-serif;padding:40px;text-align:center;'>"
                        f"<h2>⚠️ Please use HTTP instead of HTTPS</h2>"
                        f"<p>This local development server runs on plain HTTP.</p>"
                        f"<p><a href='http://127.0.0.1:{port}/' style='font-size:20px;font-weight:bold;color:#16a34a;'>Click here to open http://127.0.0.1:{port}/</a></p>"
                        f"</body></html>\r\n"
                    )
                    self.wfile.write(msg.encode("utf-8"))
                    self.wfile.flush()
                except Exception:
                    pass
                return
        except Exception:
            pass
        return super().handle_one_request()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app import app, create_app
from backend.services.db import get_db, init_db
from backend.routes.scan import detector, get_product_catalog as product_catalog
from backend.config import CROP_DIR, UPLOAD_FOLDER, REF_DIR, PRODUCT_IMG_DIR

def find_free_port(preferred_port=5001):
    import socket
    if "PORT" in os.environ:
        try:
            return int(os.environ["PORT"])
        except ValueError:
            pass
    if "INVENTO_PORT" in os.environ:
        try:
            return int(os.environ["INVENTO_PORT"])
        except ValueError:
            pass
    for p in [preferred_port, 5001, 5050, 8000]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                os.environ["INVENTO_PORT"] = str(p)
                return p
            except OSError:
                continue
    return preferred_port

if __name__ == "__main__":
    port = find_free_port(5000)
    print("\n" + "=" * 65)
    print(f"  🚀 INVENTO AI - Starting Full Stack Platform (Root Launcher)")
    print("  📁 Frontend folder : frontend/")
    print("  📁 Backend folder  : backend/")
    print(f"  🌐 Running at      : http://127.0.0.1:{port}")
    print(f"  ⚠️  NOTE           : Use HTTP, not HTTPS (http://127.0.0.1:{port})")
    print("=" * 65 + "\n")
    app.run(host="127.0.0.1", port=port, debug=True, request_handler=FriendlyWSGIRequestHandler)
