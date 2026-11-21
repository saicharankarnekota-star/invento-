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

import json
from datetime import datetime
from flask import Flask, session, send_from_directory, redirect, url_for
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

def create_app():
    app = Flask(
        __name__,
        static_folder=config.FRONTEND_DIR,
        static_url_path="",
        template_folder=config.FRONTEND_DIR
    )

    app.secret_key = config.SECRET_KEY
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

if __name__ == "__main__":
    port = find_free_port(5000)
    print("\n" + "=" * 65)
    print(f"  🚀 INVENTO AI Full Stack Application running on http://127.0.0.1:{port}")
    print("  📁 Frontend folder : frontend/")
    print("  📁 Backend folder  : backend/")
    print("  🗄️ Database        : Supabase Cloud PostgreSQL")
    print("=" * 65 + "\n")
    app.run(host="127.0.0.1", port=port, debug=True)
