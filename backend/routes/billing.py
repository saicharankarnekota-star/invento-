"""Point of Sale (POS), cart, payment verification, and billing invoices."""
import re
import secrets
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, Response, get_flashed_messages
import backend.config as config
from backend.models.product import ProductModel
from backend.models.bill import BillModel
from backend.services.db import get_db
from backend.services.barcode import ean13_svg, normalize as ean_normalize
from backend.routes.utils import login_required, to_int, to_float

billing_bp = Blueprint("billing", __name__)

PAYMENT_METHODS = ("Cash", "UPI", "Card")

def luhn_ok(number):
    total, flip = 0, False
    for ch in reversed(number):
        d = int(ch)
        if flip:
            d = d * 2 - 9 if d * 2 > 9 else d * 2
        total += d
        flip = not flip
    return total % 10 == 0

def card_brand(number):
    if number.startswith("4"):
        return "Visa"
    if re.match(r"^(5[1-5]|222[1-9]|22[3-9]|2[3-6]|27[01]|2720)", number):
        return "Mastercard"
    if number[:2] in ("34", "37"):
        return "Amex"
    if number[:2] in ("60", "65", "81", "82") or number[:3] == "508":
        return "RuPay"
    return "Card"

def validate_payment(method, form, total):
    if method == "Cash":
        received = to_float(form.get("cash_received"), 0.0)
        if received and received + 0.001 < total:
            return f"Cash received (₹{received:,.2f}) is less than the total (₹{total:,.2f}).", None
        return None, (f"Received ₹{received:,.2f}, change ₹{received - total:,.2f}" if received else "Cash")
    if method == "UPI":
        txn = re.sub(r"\s", "", form.get("upi_txn_id", ""))
        if not re.fullmatch(r"[A-Za-z0-9]{6,30}", txn):
            return "Enter the UPI transaction ID (UTR) shown after the customer pays (6-30 letters or digits).", None
        vpa = form.get("customer_upi", "").strip()
        return None, f"UPI Txn {txn.upper()}" + (f" from {vpa}" if re.fullmatch(r"[\w.\-]{2,}@[A-Za-z]{2,}", vpa) else "")
    number = re.sub(r"[\s-]", "", form.get("card_number", ""))
    if not (number.isdigit() and 13 <= len(number) <= 19 and luhn_ok(number)):
        return "That card number is not valid. Check the digits and try again.", None
    if len(form.get("card_name", "").strip()) < 2:
        return "Enter the name on the card.", None
    em = re.fullmatch(r"(\d{1,2})\s*/\s*(\d{2})", form.get("card_expiry", "").strip())
    if not em or not 1 <= int(em.group(1)) <= 12:
        return "Enter the card expiry as MM/YY.", None
    today = date.today()
    if (2000 + int(em.group(2)), int(em.group(1))) < (today.year, today.month):
        return "That card has expired.", None
    cvv = form.get("card_cvv", "").strip()
    if not (cvv.isdigit() and len(cvv) == (4 if number[:2] in ("34", "37") else 3)):
        return "Enter the card security code (CVV).", None
    return None, f"{card_brand(number)} •••• {number[-4:]} · Auth {secrets.token_hex(3).upper()}"

def is_expired(expiry_date):
    return bool(expiry_date) and expiry_date < date.today().strftime("%Y-%m-%d")

def build_cart():
    cart = session.get("cart", {})
    items = []
    for pid, qty in cart.items():
        p = ProductModel.get_by_id(int(pid))
        if p:
            items.append({
                "product": p,
                "qty": qty,
                "price": p["price"],
                "gst_rate": p["gst_rate"] or 0,
                "subtotal": round(qty * p["price"], 2)
            })
    return items

def compute_totals(items, dtype, dvalue, order_type):
    subtotal = round(sum(i["subtotal"] for i in items), 2)
    discount = subtotal * min(dvalue, 100) / 100 if dtype == "percent" else min(dvalue, subtotal)
    discount = round(max(discount, 0), 2)
    gst = 0.0
    for i in items:
        share = round(discount * i["subtotal"] / subtotal, 2) if subtotal else 0.0
        i["disc"] = share
        i["gst"] = round((i["subtotal"] - share) * i["gst_rate"] / 100, 2)
        gst += i["gst"]
    gst = round(gst, 2)
    taxable = round(subtotal - discount, 2)
    fee = config.DELIVERY_FEE if (order_type == "delivery" and items and taxable < config.FREE_DELIVERY_ABOVE) else 0.0
    cgst = round(gst / 2, 2)
    return {
        "subtotal": subtotal,
        "discount": discount,
        "gst": gst,
        "cgst": cgst,
        "sgst": round(gst - cgst, 2),
        "delivery_fee": fee,
        "total": round(taxable + gst + fee, 2)
    }

def cart_context():
    items = build_cart()
    discount = session.get("discount", {"type": "percent", "value": 0})
    order_type = session.get("order_type", "store")
    totals = compute_totals(items, discount["type"], discount["value"], order_type)
    return {
        "cart_items": items,
        "totals": totals,
        "discount": discount,
        "order_type": order_type,
        "free_delivery_above": config.FREE_DELIVERY_ABOVE,
        "delivery_fee_amount": config.DELIVERY_FEE
    }

def add_to_cart_helper(product_id, qty=1):
    p = ProductModel.get_by_id(product_id)
    if not p:
        return False, "Product not found."
    if is_expired(p["expiry_date"]):
        return False, f"{p['name']} has expired and cannot be sold."
    if p["quantity"] <= 0:
        return False, f"{p['name']} is out of stock."
    cart = dict(session.get("cart", {}))
    current = cart.get(str(product_id), 0)
    new = min(current + qty, p["quantity"])
    if new == current:
        return False, f"Only {p['quantity']} units of {p['name']} are in stock."
    cart[str(product_id)] = new
    session["cart"] = cart
    note = "" if new == current + qty else f" (only {p['quantity']} in stock)"
    return True, f"Added {new - current} x {p['name']} to your cart{note}."

def cart_response():
    if request.headers.get("X-Requested-With") != "fetch":
        return redirect(url_for("billing.billing", q=request.form.get("q", ""), category=request.form.get("category", "")))
    ctx = cart_context()
    return jsonify(
        cart=session.get("cart", {}),
        count=sum(session.get("cart", {}).values()),
        total=ctx["totals"]["total"],
        empty=not ctx["cart_items"],
        order_type=ctx["order_type"],
        html=render_template("_cart_dynamic.html", **ctx),
        messages=[{"category": c, "message": m} for c, m in get_flashed_messages(with_categories=True)]
    )

@billing_bp.route("/barcode/<code>.svg")
@login_required
def barcode_image(code):
    svg = ean13_svg(code)
    if not svg:
        return Response("Only valid EAN-13 / UPC-A codes can be drawn.", status=404)
    return Response(svg, mimetype="image/svg+xml")

@billing_bp.route("/api/barcode/<code>")
@login_required
def api_barcode(code):
    row = ProductModel.get_by_barcode(code)
    if not row:
        return jsonify(found=False, barcode=code), 404
    return jsonify(found=True, **dict(row))

@billing_bp.route("/billing")
@login_required
def billing():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    if q:
        code = ean_normalize(q) or q
        hit = ProductModel.get_by_barcode(code) if re.fullmatch(r"[A-Za-z0-9\-]{4,24}", code) else None
        if hit:
            ok, msg = add_to_cart_helper(hit["id"], 1)
            flash(msg, "success" if ok else "warning")
            return redirect(url_for("billing.billing", category=category))

    categories = ProductModel.get_categories()
    today_str = date.today().strftime("%Y-%m-%d")
    all_products = ProductModel.get_all(search_query=q, category=category)
    # Filter only available and non-expired items
    sellable = [p for p in all_products if p["quantity"] > 0 and (not p["expiry_date"] or p["expiry_date"] >= today_str)]

    ctx = cart_context()
    return render_template(
        "billing.html",
        products=sellable,
        categories=categories,
        q=q,
        selected_category=category,
        in_cart=session.get("cart", {}),
        merchant_upi=config.MERCHANT_UPI_ID,
        merchant_name=config.MERCHANT_NAME,
        **ctx
    )

@billing_bp.route("/cart/add/<int:product_id>", methods=["POST"])
@login_required
def cart_add(product_id):
    ok, msg = add_to_cart_helper(product_id, 1)
    if not ok:
        flash(msg, "warning")
    return cart_response()

@billing_bp.route("/cart/update/<int:product_id>", methods=["POST"])
@login_required
def cart_update(product_id):
    qty = to_int(request.form.get("qty"), 1)
    cart = dict(session.get("cart", {}))
    p = ProductModel.get_by_id(product_id)
    if qty == 0 or not p:
        cart.pop(str(product_id), None)
    else:
        if qty > p["quantity"]:
            flash(f"Only {p['quantity']} units of {p['name']} are in stock.", "warning")
            qty = p["quantity"]
        cart[str(product_id)] = qty
    session["cart"] = cart
    return cart_response()

@billing_bp.route("/cart/remove/<int:product_id>", methods=["POST"])
@login_required
def cart_remove(product_id):
    cart = dict(session.get("cart", {}))
    cart.pop(str(product_id), None)
    session["cart"] = cart
    return cart_response()

@billing_bp.route("/cart/clear", methods=["POST"])
@login_required
def cart_clear():
    for key in ("cart", "discount", "order_type"):
        session.pop(key, None)
    flash("Cart cleared.", "info")
    return cart_response()

@billing_bp.route("/cart/options", methods=["POST"])
@login_required
def cart_options():
    if request.form.get("order_type") in ("store", "delivery"):
        session["order_type"] = request.form["order_type"]
    if "discount_type" in request.form:
        dtype = request.form.get("discount_type")
        dtype = dtype if dtype in ("percent", "flat") else "percent"
        value = to_float(request.form.get("discount_value"), 0.0)
        if dtype == "percent" and value > 100:
            value = 100.0
            flash("A discount cannot be more than 100%.", "warning")
        session["discount"] = {"type": dtype, "value": value}
    return cart_response()

@billing_bp.route("/checkout", methods=["POST"])
@login_required
def checkout():
    if not session.get("cart"):
        flash("The cart is empty. Add products before generating a bill.", "warning")
        return redirect(url_for("billing.billing"))

    customer = request.form.get("customer_name", "").strip()[:80] or "Walk-in Customer"
    phone = request.form.get("customer_phone", "").strip()[:20]
    payment = request.form.get("payment_method", "Cash")
    payment = payment if payment in PAYMENT_METHODS else "Cash"
    order_type = session.get("order_type", "store")
    discount = session.get("discount", {"type": "percent", "value": 0})
    address = request.form.get("address", "").strip()[:200]

    if order_type == "delivery" and not address:
        flash("Enter a delivery address for home-delivery orders.", "danger")
        return redirect(url_for("billing.billing"))

    items = build_cart()
    if not items:
        flash("The cart is empty. Add products before generating a bill.", "warning")
        return redirect(url_for("billing.billing"))

    for it in items:
        p = it["product"]
        if p["quantity"] < it["qty"] or is_expired(p["expiry_date"]):
            flash(f"{p['name']} is no longer available in the requested quantity. Update the cart and try again.", "danger")
            return redirect(url_for("billing.billing"))

    totals = compute_totals(items, discount["type"], discount["value"], order_type)
    pay_error, pay_ref = validate_payment(payment, request.form, totals["total"])
    if pay_error:
        flash(pay_error, "danger")
        return redirect(url_for("billing.billing"))

    try:
        bill_dict = {
            "customer_name": customer,
            "customer_phone": phone,
            "payment_method": payment,
            "total": totals["total"],
            "cashier": session.get("user"),
            "subtotal": totals["subtotal"],
            "discount_type": discount["type"],
            "discount_value": discount["value"],
            "discount_amount": totals["discount"],
            "gst_amount": totals["gst"],
            "delivery_fee": totals["delivery_fee"],
            "order_type": order_type,
            "address": address,
            "payment_ref": pay_ref
        }
        bill_id, bill_no = BillModel.create(bill_dict, items)
    except Exception:
        flash("Could not generate the bill. Nothing was charged; please try again.", "danger")
        return redirect(url_for("billing.billing"))

    for key in ("cart", "discount", "order_type"):
        session.pop(key, None)
    flash(f"Bill {bill_no} generated. Stock has been updated.", "success")
    return redirect(url_for("billing.bill_detail", bill_id=bill_id))

@billing_bp.route("/bills")
@login_required
def bills():
    q = request.args.get("q", "").strip()
    day = request.args.get("date", "").strip()
    bill_rows = BillModel.get_all(search_query=q, date_filter=day)
    stats = BillModel.get_metrics()
    return render_template(
        "bills.html",
        bills=bill_rows,
        q=q,
        day=day,
        today_count=stats["today_count"],
        today_sales=stats["today_sales"],
        all_count=stats["all_count"],
        all_sales=stats["all_sales"]
    )

@billing_bp.route("/bills/<int:bill_id>")
@login_required
def bill_detail(bill_id):
    bill, items = BillModel.get_by_id(bill_id)
    if not bill:
        flash("Bill not found.", "danger")
        return redirect(url_for("billing.bills"))
    gst = bill["gst_amount"] or 0
    cgst = round(gst / 2, 2)
    return render_template(
        "bill_detail.html",
        bill=bill,
        items=items,
        units=sum(i["quantity"] for i in items),
        cgst=cgst,
        sgst=round(gst - cgst, 2)
    )
