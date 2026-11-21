"""Smart natural language assistant endpoint for queries, recommendations, and cart actions."""
from flask import Blueprint, request, jsonify, url_for, session
from backend.services.db import get_db
from backend.services import assistant
from backend.routes.billing import add_to_cart_helper
from backend.routes.utils import login_required

assistant_bp = Blueprint("assistant", __name__)

@assistant_bp.route("/api/assistant", methods=["POST"])
@login_required
def api_assistant():
    message = ((request.get_json(silent=True) or {}).get("message") or "").strip()[:300]
    if not message:
        return jsonify(reply="Type a question and I'll look it up.", items=[], links=[], chips=assistant.CHIPS)

    urls = {
        "billing": url_for("billing.billing"),
        "bills": url_for("billing.bills"),
        "alerts": url_for("inventory.alerts"),
        "reports": url_for("reports.reports"),
        "scan": url_for("scan.scan"),
        "dashboard": url_for("inventory.dashboard"),
        "products": url_for("inventory.products")
    }

    conn = get_db()
    result = assistant.answer(
        message,
        conn,
        lambda pid, qty: add_to_cart_helper(pid, qty),
        urls,
        lambda bid: url_for("billing.bill_detail", bill_id=bid)
    )
    conn.close()

    result["cart_count"] = sum(session.get("cart", {}).values())
    return jsonify(result)
