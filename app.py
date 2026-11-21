"""INVENTO AI Application Root Entrypoint.
Delegates to backend/app.py to run the full stack server.
"""
import sys
import os

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
    print("=" * 65 + "\n")
    app.run(host="127.0.0.1", port=port, debug=True)
