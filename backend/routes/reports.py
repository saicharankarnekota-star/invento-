"""Valuation reports, category summaries, restock recommendations, and CSV export."""
import io
import csv
from datetime import date, timedelta
from flask import Blueprint, render_template, Response
from backend.services.db import get_db
from backend.routes.utils import login_required, get_expiry_info

reports_bp = Blueprint("reports", __name__)

@reports_bp.route("/reports")
@login_required
def reports():
    conn = get_db()
    cursor = conn.cursor()

    # All products
    cursor.execute("SELECT * FROM products ORDER BY category ASC, name ASC")
    products = cursor.fetchall()

    # Totals
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(quantity), 0), COALESCE(SUM(quantity * price), 0) FROM products")
    total_products, total_stock, total_valuation = cursor.fetchone()

    # Category summaries
    cursor.execute("""
        SELECT category, COUNT(*) as count, SUM(quantity) as stock, SUM(quantity * price) as val
        FROM products
        GROUP BY category
    """)
    category_summary = cursor.fetchall()

    # Restock recommendations
    cursor.execute("""
        SELECT *, (reorder_level * 2 - quantity) as recommended_reorder,
               ((reorder_level * 2 - quantity) * price) as estimated_cost
        FROM products
        WHERE quantity <= reorder_level
    """)
    restock_needs = cursor.fetchall()

    # Expiry Risk Analysis
    in_7_days_str = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT *, (quantity * price) as risk_val
        FROM products
        WHERE expiry_date IS NOT NULL AND expiry_date != '' AND expiry_date <= ? AND quantity > 0
        ORDER BY expiry_date ASC
    """, (in_7_days_str,))
    expiry_risk_items = cursor.fetchall()

    total_expiry_risk_val = sum(r["risk_val"] for r in expiry_risk_items)
    conn.close()

    return render_template(
        "reports.html",
        products=products,
        total_products=total_products,
        total_stock=total_stock,
        total_valuation=total_valuation,
        category_summary=category_summary,
        restock_needs=restock_needs,
        expiry_risk_items=expiry_risk_items,
        total_expiry_risk_val=total_expiry_risk_val
    )

@reports_bp.route("/reports/export-csv")
@login_required
def export_csv():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, category, barcode, quantity, reorder_level, price, (quantity * price) as value, expiry_date, last_updated FROM products")
    rows = cursor.fetchall()
    conn.close()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Product ID", "Product Name", "Category", "Barcode", "Quantity", "Reorder Level", "Price (INR)", "Total Value (INR)", "Expiry Date", "Shelf Status", "Last Updated"])
    for r in rows:
        exp_info = get_expiry_info(r["expiry_date"])
        writer.writerow([
            r["id"],
            r["name"],
            r["category"],
            f'\t{r["barcode"] or ""}' if r["barcode"] else "",
            r["quantity"],
            r["reorder_level"],
            f'{r["price"]:.2f}',
            f'{r["value"]:.2f}',
            r["expiry_date"] or "N/A",
            exp_info["label"],
            r["last_updated"]
        ])
    csv_data = buf.getvalue()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=INVENTO_AI_Inventory_Report.csv"}
    )
