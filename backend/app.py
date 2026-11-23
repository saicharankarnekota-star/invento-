"""INVENTO AI Backend Application.
Modular, full-stack Flask API and web portal configured for Vercel and Supabase.
"""
import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

if "backend" not in sys.modules:
    import types
    backend_pkg = types.ModuleType("backend")
    backend_pkg.__path__ = [CURRENT_DIR]
    backend_pkg.__file__ = os.path.join(CURRENT_DIR, "__init__.py")
    sys.modules["backend"] = backend_pkg

import json
import socket
from datetime import datetime, timedelta
from flask import Flask, session, send_from_directory, redirect, url_for
try:
    from werkzeug.serving import WSGIRequestHandler
except ImportError:
    from http.server import BaseHTTPRequestHandler as WSGIRequestHandler
import backend.config as config
from backend.services.db import init_db
from backend.routes.utils import get_expiry_info

# Route Blueprints
from backend.routes.auth import auth_bp
from backend.routes.inventory import inventory_bp
from backend.routes.billing import billing_bp
from backend.routes.scan import scan_bp
from backend.routes.reports import reports_bp
from backend.routes.assistant import assistant_bp

def _parse_dt(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return None

from urllib.parse import parse_qs, urlencode

class VercelPathMiddleware:
    """WSGI middleware to ensure Vercel rewrites preserve original URL paths."""
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        query_string = environ.get("QUERY_STRING", "")
        if "__route__" in query_string:
            qs_dict = parse_qs(query_string, keep_blank_values=True)
            if "__route__" in qs_dict:
                route_val = qs_dict.pop("__route__")[0]
                target_path = "/" + route_val.lstrip("/")
                environ["PATH_INFO"] = target_path
                clean_items = []
                for k, v_list in qs_dict.items():
                    for v in v_list:
                        clean_items.append((k, v))
                environ["QUERY_STRING"] = urlencode(clean_items)
                return self.wsgi_app(environ, start_response)

        path_info = environ.get("PATH_INFO", "")
        matched_path = environ.get("HTTP_X_MATCHED_PATH") or environ.get("x-matched-path")
        forwarded_uri = environ.get("HTTP_X_FORWARDED_URI") or environ.get("x-forwarded-uri")

        if path_info in ("/api/index", "/api", "/api/index.py"):
            if matched_path and not matched_path.startswith("/api/index") and matched_path != "/api":
                environ["PATH_INFO"] = matched_path
            elif forwarded_uri and not forwarded_uri.startswith("/api/index"):
                environ["PATH_INFO"] = forwarded_uri.split("?")[0]
            else:
                environ["PATH_INFO"] = "/"
        elif matched_path and matched_path != path_info:
            if not matched_path.startswith("/api/index") and not path_info.startswith(("/static", "/uploads", "/css", "/js", "/img")):
                environ["PATH_INFO"] = matched_path

        return self.wsgi_app(environ, start_response)

def create_app():
    app = Flask(
        __name__,
        static_folder=config.FRONTEND_DIR,
        static_url_path="",
        template_folder=config.FRONTEND_DIR
    )

    app.secret_key = config.SECRET_KEY
    app.config["SESSION_COOKIE_NAME"] = "invento_session"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_PATH"] = "/"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
    app.config["UPLOAD_FOLDER"] = config.UPLOAD_FOLDER
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH

    # Custom Jinja filters
    app.jinja_env.filters["from_json"] = lambda s: json.loads(s) if s else {}
    app.jinja_env.filters["expiry_info"] = get_expiry_info
    app.jinja_env.filters["fmt_date"] = lambda v: _parse_dt(v).strftime("%d %b %Y") if _parse_dt(v) else (v or "")
    app.jinja_env.filters["fmt_time"] = lambda v: _parse_dt(v).strftime("%I:%M %p") if _parse_dt(v) else ""

    # Global context processor
    @app.context_processor
    def inject_globals():
        cart = session.get("cart", {})
        return {
            "cart_count": sum(cart.values()) if isinstance(cart, dict) else 0,
            "payment_breakdown": {"Cash": 0.0, "UPI": 0.0, "Card": 0.0},
            "staff_members": []
        }

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(scan_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(assistant_bp)

    # Route aliases for seamless template & test compatibility
    aliases = [
        ("dashboard", "/dashboard", "inventory.dashboard", ["GET"]),
        ("products", "/products", "inventory.products", ["GET"]),
        ("add_product", "/products/add", "inventory.add_product", ["GET", "POST"]),
        ("edit_product", "/products/edit/<int:product_id>", "inventory.edit_product", ["GET", "POST"]),
        ("delete_product", "/products/delete/<int:product_id>", "inventory.delete_product", ["POST"]),
        ("alerts", "/alerts", "inventory.alerts", ["GET"]),
        ("restock_product", "/alerts/restock/<int:product_id>", "inventory.restock_product", ["POST"]),
        ("dispose_product", "/alerts/dispose/<int:product_id>", "inventory.dispose_product", ["POST"]),
        ("billing", "/billing", "billing.billing", ["GET"]),
        ("cart_add", "/cart/add/<int:product_id>", "billing.cart_add", ["POST"]),
        ("cart_update", "/cart/update/<int:product_id>", "billing.cart_update", ["POST"]),
        ("cart_remove", "/cart/remove/<int:product_id>", "billing.cart_remove", ["POST"]),
        ("cart_clear", "/cart/clear", "billing.cart_clear", ["POST"]),
        ("cart_options", "/cart/options", "billing.cart_options", ["POST"]),
        ("checkout", "/checkout", "billing.checkout", ["POST"]),
        ("bills", "/bills", "billing.bills", ["GET"]),
        ("bill_detail", "/bills/<int:bill_id>", "billing.bill_detail", ["GET"]),
        ("scan", "/scan", "scan.scan", ["GET", "POST"]),
        ("sync_scan_to_inventory", "/scan/sync", "scan.sync_scan", ["POST"]),
        ("reports", "/reports", "reports.reports", ["GET"]),
        ("export_csv", "/reports/export-csv", "reports.export_csv", ["GET"]),
        ("login", "/login", "auth.login", ["GET", "POST"]),
        ("register", "/register", "auth.register", ["GET", "POST"]),
        ("logout", "/logout", "auth.logout", ["GET"]),
    ]

    for endpoint_name, rule, target, methods in aliases:
        if target in app.view_functions and endpoint_name not in app.view_functions:
            app.add_url_rule(rule, endpoint=endpoint_name, view_func=app.view_functions[target], methods=methods)

    # Serve static assets and user uploads
    @app.route("/static/<path:filename>")
    def serve_static(filename):
        if filename.startswith("uploads/"):
            subpath = filename[len("uploads/"):]
            return send_from_directory(config.UPLOAD_FOLDER, subpath)
        return send_from_directory(config.FRONTEND_DIR, filename)

    @app.route("/uploads/<path:filename>")
    def serve_uploads(filename):
        return send_from_directory(config.UPLOAD_FOLDER, filename)

    @app.route("/css/<path:filename>")
    def serve_css(filename):
        return send_from_directory(os.path.join(config.FRONTEND_DIR, "css"), filename)

    @app.route("/js/<path:filename>")
    def serve_js(filename):
        return send_from_directory(os.path.join(config.FRONTEND_DIR, "js"), filename)

    @app.route("/img/<path:filename>")
    def serve_img(filename):
        return send_from_directory(os.path.join(config.FRONTEND_DIR, "img"), filename)

    # Vercel entrypoint fallback routes
    @app.route("/api/index")
    @app.route("/api/index.py")
    @app.route("/api")
    def vercel_entrypoint_fallback():
        if "user" in session:
            return redirect(url_for("inventory.dashboard"))
        return redirect(url_for("auth.login"))

    # Wrap WSGI app with Vercel path-restoring middleware
    app.wsgi_app = VercelPathMiddleware(app.wsgi_app)

    # Initialize DB tables & seed items
    with app.app_context():
        init_db()

    return app

app = create_app()

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

try:
    from werkzeug.serving import WSGIRequestHandler
except ImportError:
    from http.server import BaseHTTPRequestHandler as WSGIRequestHandler

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

if __name__ == "__main__":
    import signal
    def _sig_handler(sig, frame):
        print("\n🛑 INVENTO Server stopped. Goodbye!\n")
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, _sig_handler)
        signal.signal(signal.SIGTERM, _sig_handler)
    except Exception:
        pass

    port = find_free_port(5000)
    print("\n" + "=" * 65)
    print(f"  🚀 INVENTO AI Full Stack Application running on http://127.0.0.1:{port}")
    print("  📁 Frontend folder : frontend/")
    print("  📁 Backend folder  : backend/")
    print("  🗄️ Database        : Supabase Cloud PostgreSQL")
    print(f"  ⚠️  NOTE           : Use HTTP, not HTTPS (http://127.0.0.1:{port})")
    print("  🛑 To stop server  : Press physical keys [Control + C] or type 'stop'")
    print("=" * 65 + "\n")
    try:
        app.run(host="127.0.0.1", port=port, debug=True, request_handler=FriendlyWSGIRequestHandler)
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 INVENTO Server stopped. Goodbye!\n")
        sys.exit(0)
