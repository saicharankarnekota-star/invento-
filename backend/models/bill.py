"""Bill and POS transaction model."""
from datetime import datetime, date
from backend.services.db import get_db

class BillModel:
    @staticmethod
    def get_by_id(bill_id):
        conn = get_db()
        bill = conn.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)).fetchone()
        if not bill:
            conn.close()
            return None, []
        items = conn.execute("""
            SELECT bi.*, p.image, p.category
            FROM bill_items bi
            LEFT JOIN products p ON p.id = bi.product_id
            WHERE bi.bill_id = ?
        """, (bill_id,)).fetchall()
        conn.close()
        return bill, items

    @staticmethod
    def get_all(search_query="", date_filter="", limit=300):
        conn = get_db()
        sql = """
            SELECT b.*,
                   (SELECT group_concat(name || ' x ' || quantity, ', ') FROM bill_items WHERE bill_id = b.id) AS items_text,
                   (SELECT COALESCE(SUM(quantity), 0) FROM bill_items WHERE bill_id = b.id) AS units
            FROM bills b WHERE 1=1
        """
        params = []
        if search_query:
            sql += " AND (b.bill_no LIKE ? OR b.customer_name LIKE ? OR b.customer_phone LIKE ?)"
            params.extend([f"%{search_query}%"] * 3)
        if date_filter:
            sql += " AND substr(b.created_at, 1, 10) = ?"
            params.append(date_filter)

        sql += f" ORDER BY b.id DESC LIMIT {int(limit)}"
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return rows

    @staticmethod
    def get_metrics():
        conn = get_db()
        today = date.today().strftime("%Y-%m-%d")
        today_row = conn.execute("SELECT COUNT(*), COALESCE(SUM(total), 0) FROM bills WHERE substr(created_at, 1, 10) = ?", (today,)).fetchone()
        all_row = conn.execute("SELECT COUNT(*), COALESCE(SUM(total), 0) FROM bills").fetchone()
        conn.close()
        return {
            "today_count": today_row[0],
            "today_sales": today_row[1],
            "all_count": all_row[0],
            "all_sales": all_row[1]
        }

    @staticmethod
    def get_shift_metrics(cashier_name=None):
        conn = get_db()
        today = date.today().strftime("%Y-%m-%d")
        sql = "SELECT payment_method, COUNT(*) as count, COALESCE(SUM(total), 0) as total FROM bills WHERE substr(created_at, 1, 10) = ?"
        params = [today]
        if cashier_name:
            sql += " AND cashier = ?"
            params.append(cashier_name)
        sql += " GROUP BY payment_method"
        rows = conn.execute(sql, params).fetchall()

        breakdown = {"Cash": 0.0, "UPI": 0.0, "Card": 0.0}
        total_sales = 0.0
        total_bills = 0
        for r in rows:
            pm = r["payment_method"]
            amt = float(r["total"] or 0.0)
            cnt = int(r["count"] or 0)
            if pm in breakdown:
                breakdown[pm] = amt
            else:
                breakdown[pm] = amt
            total_sales += amt
            total_bills += cnt

        conn.close()
        avg_bill = round(total_sales / total_bills, 2) if total_bills else 0.0
        return {
            "total_sales": total_sales,
            "total_bills": total_bills,
            "avg_bill": avg_bill,
            "breakdown": breakdown
        }

    @staticmethod
    def create(bill_dict, items_list):
        conn = get_db()
        try:
            now = datetime.now()
            stamp = now.strftime("%Y-%m-%d %H:%M:%S")
            today_str = now.strftime("%Y-%m-%d")

            count_row = conn.execute("SELECT COUNT(*) FROM bills WHERE substr(created_at, 1, 10) = ?", (today_str,)).fetchone()
            count_today = count_row[0] if count_row else 0
            bill_no = f"INV-{now.strftime('%Y%m%d')}-{count_today + 1:04d}"

            cur = conn.execute("""
                INSERT INTO bills (
                    bill_no, customer_name, customer_phone, payment_method, total, cashier,
                    created_at, subtotal, discount_type, discount_value, discount_amount,
                    gst_amount, delivery_fee, order_type, address, payment_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bill_no,
                bill_dict.get("customer_name") or "Walk-in Customer",
                bill_dict.get("customer_phone", ""),
                bill_dict.get("payment_method", "Cash"),
                bill_dict.get("total", 0.0),
                bill_dict.get("cashier", "Store Admin"),
                stamp,
                bill_dict.get("subtotal", 0.0),
                bill_dict.get("discount_type", "percent"),
                bill_dict.get("discount_value", 0.0),
                bill_dict.get("discount_amount", 0.0),
                bill_dict.get("gst_amount", 0.0),
                bill_dict.get("delivery_fee", 0.0),
                bill_dict.get("order_type", "store"),
                bill_dict.get("address", ""),
                bill_dict.get("payment_ref", "")
            ))
            bill_id = cur.lastrowid

            for item in items_list:
                p = item["product"]
                conn.execute("""
                    INSERT INTO bill_items (bill_id, product_id, name, quantity, unit_price, subtotal, gst_rate, gst_amount, discount_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    bill_id,
                    p["id"],
                    p["name"],
                    item["qty"],
                    item["price"],
                    item["subtotal"],
                    item.get("gst_rate", 0),
                    item.get("gst", 0),
                    item.get("disc", 0)
                ))
                conn.execute("UPDATE products SET quantity = quantity - ?, last_updated = ? WHERE id = ?",
                             (item["qty"], stamp, p["id"]))

            conn.commit()
            return bill_id, bill_no
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
