"""Inventory management, products CRUD, alerts, and dashboard routes."""
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from backend.models.product import ProductModel
from backend.models.bill import BillModel
from backend.models.scan import ScanModel
from backend.models.user import UserModel
from backend.services.barcode import clean_barcode
from backend.routes.utils import login_required, to_int, to_float, save_product_image, remove_product_image

inventory_bp = Blueprint("inventory", __name__)

@inventory_bp.route("/dashboard")
@login_required
def dashboard():
    user_role = session.get("role", "admin")
    role_view = request.args.get("role_view", "").strip()
    if role_view in ("admin", "inventory_manager", "cashier") and (user_role == "admin" or session.get("role") == role_view):
        active_role = role_view
    else:
        active_role = user_role

    metrics = ProductModel.get_dashboard_metrics()
    recent_scans = ScanModel.get_recent(limit=4)
    recent_bills = BillModel.get_all(limit=6)
    bill_stats = BillModel.get_metrics()
    staff_members = UserModel.get_all()

    # 1. Cashier Frontline Shift Dashboard
    if active_role in ("cashier", "staff"):
        cashier_name = session.get("user")
        shift_data = BillModel.get_shift_metrics(cashier_name=cashier_name)
        all_products = ProductModel.get_all()
        return render_template(
            "dashboard_cashier.html",
            active_role=active_role,
            shift_data=shift_data,
            recent_bills=recent_bills,
            products=all_products
        )

    # 2. Inventory Operations & Stock Dashboard
    elif active_role == "inventory_manager":
        inv_data = ProductModel.get_inventory_manager_data()
        return render_template(
            "dashboard_inventory.html",
            active_role=active_role,
            total_products=metrics["total_products"],
            total_stock=metrics["total_stock"],
            low_stock_count=metrics["low_stock_count"],
            expired_count=metrics["expired_count"],
            expiring_soon_count=metrics["expiring_soon_count"],
            out_of_stock_count=inv_data["out_of_stock_count"],
            restock_needs=inv_data["restock_needs"],
            expiry_risk_items=inv_data["expiry_risk_items"],
            recent_scans=recent_scans
        )

    # 3. Executive Admin Dashboard (Default)
    else:
        shift_totals = BillModel.get_shift_metrics()
        return render_template(
            "dashboard_admin.html",
            active_role=active_role,
            recent_bills=recent_bills,
            today_bills=bill_stats["today_count"],
            today_sales=bill_stats["today_sales"],
            total_products=metrics["total_products"],
            total_stock=metrics["total_stock"],
            total_valuation=metrics["total_valuation"],
            low_stock_count=metrics["low_stock_count"],
            expired_count=metrics["expired_count"],
            expiring_soon_count=metrics["expiring_soon_count"],
            low_stock_items=metrics["low_stock_items"],
            expiring_items=metrics["expiring_items"],
            categories_data=metrics["categories_data"],
            recent_scans=recent_scans,
            staff_members=staff_members,
            payment_breakdown=shift_totals["breakdown"]
        )

@inventory_bp.route("/products")
@login_required
def products():
    search_query = request.args.get("q", "").strip()
    category_filter = request.args.get("category", "").strip()
    expiry_filter = request.args.get("expiry_status", "").strip()

    items = ProductModel.get_all(search_query, category_filter, expiry_filter)
    categories = ProductModel.get_categories()

    return render_template(
        "products.html",
        products=items,
        categories=categories,
        search_query=search_query,
        selected_category=category_filter,
        selected_expiry=expiry_filter
    )

@inventory_bp.route("/products/add", methods=["GET", "POST"])
@login_required
def add_product():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        quantity = to_int(request.form.get("quantity"), 0)
        reorder_level = to_int(request.form.get("reorder_level"), 5)
        price = to_float(request.form.get("price"), 0.0)
        description = request.form.get("description", "").strip()
        expiry_date = request.form.get("expiry_date", "").strip()
        barcode = clean_barcode(request.form.get("barcode"))
        gst_rate = min(to_float(request.form.get("gst_rate"), 5.0), 28.0)

        if not name or not category:
            flash("Product name and category are required!", "danger")
            return redirect(url_for("inventory.add_product"))
        if barcode is None:
            flash("Barcode must be 4-24 letters/digits (an EAN-13 or UPC-A code is best).", "danger")
            return redirect(url_for("inventory.add_product"))

        if barcode:
            existing = ProductModel.get_by_barcode(barcode)
            if existing:
                flash(f"Barcode {barcode} already belongs to another product.", "danger")
                return redirect(url_for("inventory.add_product"))

        new_image = save_product_image(request.files.get("image"))
        ProductModel.create({
            "name": name,
            "category": category,
            "quantity": quantity,
            "reorder_level": reorder_level,
            "price": price,
            "description": description,
            "expiry_date": expiry_date,
            "barcode": barcode,
            "gst_rate": gst_rate,
            "image": new_image
        })

        flash(f"Product '{name}' added successfully!", "success")
        return redirect(url_for("inventory.products"))

    return render_template("add_product.html")

@inventory_bp.route("/products/edit/<int:product_id>", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    product = ProductModel.get_by_id(product_id)
    if not product:
        flash("Product not found!", "danger")
        return redirect(url_for("inventory.products"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        quantity = to_int(request.form.get("quantity"), 0)
        reorder_level = to_int(request.form.get("reorder_level"), 5)
        price = to_float(request.form.get("price"), 0.0)
        description = request.form.get("description", "").strip()
        expiry_date = request.form.get("expiry_date", "").strip()
        barcode = clean_barcode(request.form.get("barcode"))
        gst_rate = min(to_float(request.form.get("gst_rate"), 5.0), 28.0)

        if barcode is None:
            flash("Barcode must be 4-24 letters/digits (an EAN-13 or UPC-A code is best).", "danger")
            return redirect(url_for("inventory.edit_product", product_id=product_id))

        if barcode:
            existing = ProductModel.get_by_barcode(barcode)
            if existing and existing["id"] != product_id:
                flash(f"Barcode {barcode} already belongs to another product.", "danger")
                return redirect(url_for("inventory.edit_product", product_id=product_id))

        update_data = {
            "name": name,
            "category": category,
            "quantity": quantity,
            "reorder_level": reorder_level,
            "price": price,
            "description": description,
            "expiry_date": expiry_date,
            "barcode": barcode,
            "gst_rate": gst_rate
        }

        new_image = save_product_image(request.files.get("image"))
        if new_image:
            update_data["image"] = new_image
            remove_product_image(product["image"])

        ProductModel.update(product_id, update_data)
        flash(f"Product '{name}' updated successfully!", "success")
        return redirect(url_for("inventory.products"))

    return render_template("edit_product.html", product=product)

@inventory_bp.route("/products/delete/<int:product_id>", methods=["POST"])
@login_required
def delete_product(product_id):
    old_img = ProductModel.delete(product_id)
    remove_product_image(old_img)
    flash("Product deleted successfully.", "info")
    return redirect(url_for("inventory.products"))

@inventory_bp.route("/alerts")
@login_required
def alerts():
    items = ProductModel.get_all()
    today_str = date.today().strftime("%Y-%m-%d")
    in_7_days_str = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")

    out_of_stock = [p for p in items if p["quantity"] == 0]
    low_stock = [p for p in items if 0 < p["quantity"] <= p["reorder_level"]]
    expired = [p for p in items if p["expiry_date"] and p["expiry_date"] < today_str and p["quantity"] > 0]
    expiring_soon = [p for p in items if p["expiry_date"] and today_str <= p["expiry_date"] <= in_7_days_str and p["quantity"] > 0]

    return render_template(
        "alerts.html",
        out_of_stock=out_of_stock,
        low_stock=low_stock,
        expired_products=expired,
        expiring_soon_products=expiring_soon
    )

@inventory_bp.route("/alerts/restock/<int:product_id>", methods=["POST"])
@login_required
def restock_product(product_id):
    add_qty = to_int(request.form.get("quantity"), 10, minimum=1)
    p = ProductModel.restock(product_id, add_qty)
    if not p:
        flash("Product not found.", "danger")
    else:
        flash(f"Restocked '{p['name']}'. New stock quantity: {p['quantity']}.", "success")
    return redirect(url_for("inventory.alerts"))

@inventory_bp.route("/alerts/dispose/<int:product_id>", methods=["POST"])
@login_required
def dispose_product(product_id):
    p = ProductModel.dispose(product_id)
    if not p:
        flash("Product not found.", "danger")
    else:
        flash(f"Expired stock for '{p['name']}' has been disposed and cleared from shelf inventory.", "warning")
    return redirect(url_for("inventory.alerts"))
