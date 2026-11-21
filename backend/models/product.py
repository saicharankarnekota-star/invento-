"""Product model and inventory operations."""
from datetime import datetime, date, timedelta
from backend.services.db import get_db
from backend.services.barcode import make_internal_ean13, normalize as ean_normalize

class ProductModel:
    @staticmethod
    def get_all(search_query="", category="", expiry_filter=""):
        conn = get_db()
        query = "SELECT * FROM products WHERE 1=1"
        params = []

        if search_query:
            query += " AND (name LIKE ? OR category LIKE ? OR description LIKE ? OR barcode LIKE ?)"
            term = f"%{search_query}%"
            params.extend([term, term, term, term])

        if category:
            query += " AND category = ?"
            params.append(category)

        today_str = date.today().strftime("%Y-%m-%d")
        in_7_days_str = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")

        if expiry_filter == "expired":
            query += " AND expiry_date IS NOT NULL AND expiry_date != '' AND expiry_date < ?"
            params.append(today_str)
        elif expiry_filter == "expiring_soon":
            query += " AND expiry_date >= ? AND expiry_date <= ?"
            params.extend([today_str, in_7_days_str])
        elif expiry_filter == "good":
            query += " AND expiry_date > ?"
            params.append(in_7_days_str)

        query += " ORDER BY name ASC"
        items = conn.execute(query, params).fetchall()
        conn.close()
        return items

    @staticmethod
    def get_by_id(product_id):
        conn = get_db()
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        conn.close()
        return product

    @staticmethod
    def get_by_barcode(barcode):
        if not barcode:
            return None
        code = ean_normalize(barcode) or barcode
        conn = get_db()
        product = conn.execute("SELECT * FROM products WHERE barcode = ?", (code,)).fetchone()
        conn.close()
        return product

    @staticmethod
    def get_categories():
        conn = get_db()
        rows = conn.execute("SELECT DISTINCT category FROM products ORDER BY category").fetchall()
        conn.close()
        return [r["category"] for r in rows if r["category"]]

    @staticmethod
    def create(data):
        conn = get_db()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        barcode = data.get("barcode") or None
        cur = conn.execute("""
            INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate, image)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("name"),
            data.get("category"),
            data.get("quantity", 0),
            data.get("reorder_level", 5),
            data.get("price", 0.0),
            data.get("description", ""),
            data.get("expiry_date", ""),
            now,
            barcode,
            data.get("gst_rate", 5.0),
            data.get("image", None)
        ))
        new_id = cur.lastrowid
        if not barcode:
            auto_code = make_internal_ean13(new_id)
            conn.execute("UPDATE products SET barcode = ? WHERE id = ?", (auto_code, new_id))
        conn.commit()
        conn.close()
        return new_id

    @staticmethod
    def update(product_id, data):
        conn = get_db()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        barcode = data.get("barcode")
        if not barcode:
            old = conn.execute("SELECT barcode FROM products WHERE id = ?", (product_id,)).fetchone()
            barcode = old["barcode"] if old and old["barcode"] else make_internal_ean13(product_id)

        sql = """
            UPDATE products
            SET name = ?, category = ?, quantity = ?, reorder_level = ?, price = ?,
                description = ?, expiry_date = ?, last_updated = ?, barcode = ?, gst_rate = ?
        """
        params = [
            data.get("name"),
            data.get("category"),
            data.get("quantity", 0),
            data.get("reorder_level", 5),
            data.get("price", 0.0),
            data.get("description", ""),
            data.get("expiry_date", ""),
            now,
            barcode,
            data.get("gst_rate", 5.0)
        ]
        if "image" in data and data["image"] is not None:
            sql += ", image = ?"
            params.append(data["image"])

        sql += " WHERE id = ?"
        params.append(product_id)
        conn.execute(sql, params)
        conn.commit()
        conn.close()

    @staticmethod
    def delete(product_id):
        conn = get_db()
        old = conn.execute("SELECT image FROM products WHERE id = ?", (product_id,)).fetchone()
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        conn.close()
        return old["image"] if old else None

    @staticmethod
    def restock(product_id, quantity=10):
        conn = get_db()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("UPDATE products SET quantity = quantity + ?, last_updated = ? WHERE id = ?", (quantity, now_str, product_id))
        conn.commit()
        p = conn.execute("SELECT name, quantity FROM products WHERE id = ?", (product_id,)).fetchone()
        conn.close()
        return p

    @staticmethod
    def dispose(product_id):
        conn = get_db()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("UPDATE products SET quantity = 0, last_updated = ? WHERE id = ?", (now_str, product_id))
        conn.commit()
        p = conn.execute("SELECT name FROM products WHERE id = ?", (product_id,)).fetchone()
        conn.close()
        return p

    @staticmethod
    def get_dashboard_metrics():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(quantity), 0), COALESCE(SUM(quantity * price), 0) FROM products")
        total_products, total_stock, total_valuation = cursor.fetchone()

        cursor.execute("SELECT COUNT(*) FROM products WHERE quantity <= reorder_level")
        low_stock_count = cursor.fetchone()[0]

        today_str = date.today().strftime("%Y-%m-%d")
        in_7_days_str = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")

        cursor.execute("SELECT COUNT(*) FROM products WHERE expiry_date IS NOT NULL AND expiry_date != '' AND expiry_date < ? AND quantity > 0", (today_str,))
        expired_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM products WHERE expiry_date >= ? AND expiry_date <= ? AND quantity > 0", (today_str, in_7_days_str))
        expiring_soon_count = cursor.fetchone()[0]

        cursor.execute("SELECT * FROM products WHERE quantity <= reorder_level ORDER BY quantity ASC LIMIT 5")
        low_stock_items = cursor.fetchall()

        cursor.execute("SELECT * FROM products WHERE expiry_date IS NOT NULL AND expiry_date != '' AND expiry_date <= ? AND quantity > 0 ORDER BY expiry_date ASC LIMIT 5", (in_7_days_str,))
        expiring_items = cursor.fetchall()

        cursor.execute("SELECT category, COUNT(*) as count, SUM(quantity) as stock FROM products GROUP BY category")
        categories_data = cursor.fetchall()

        conn.close()
        return {
            "total_products": total_products,
            "total_stock": total_stock,
            "total_valuation": total_valuation,
            "low_stock_count": low_stock_count,
            "expired_count": expired_count,
            "expiring_soon_count": expiring_soon_count,
            "low_stock_items": low_stock_items,
            "expiring_items": expiring_items,
            "categories_data": categories_data
        }

    @staticmethod
    def get_inventory_manager_data():
        conn = get_db()
        cursor = conn.cursor()
        today_str = date.today().strftime("%Y-%m-%d")
        in_7_days_str = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")

        cursor.execute("""
            SELECT *, (reorder_level * 2 - quantity) as recommended_reorder,
                   ((reorder_level * 2 - quantity) * price) as estimated_cost
            FROM products
            WHERE quantity <= reorder_level
            ORDER BY quantity ASC LIMIT 10
        """)
        restock_needs = cursor.fetchall()

        cursor.execute("""
            SELECT *, (quantity * price) as risk_val
            FROM products
            WHERE expiry_date IS NOT NULL AND expiry_date != '' AND expiry_date <= ? AND quantity > 0
            ORDER BY expiry_date ASC LIMIT 10
        """, (in_7_days_str,))
        expiry_risk_items = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM products WHERE quantity = 0")
        out_of_stock_count = cursor.fetchone()[0]

        conn.close()
        return {
            "restock_needs": restock_needs,
            "expiry_risk_items": expiry_risk_items,
            "out_of_stock_count": out_of_stock_count
        }
