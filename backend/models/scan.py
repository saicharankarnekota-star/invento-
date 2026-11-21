"""Shelf scan history and AI recognition references."""
import json
from datetime import datetime
from backend.services.db import get_db

class ScanModel:
    @staticmethod
    def create(input_filename, annotated_filename, detected_counts, total_count):
        conn = get_db()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = conn.execute("""
            INSERT INTO scans (timestamp, original_image, annotated_image, detected_counts, total_items)
            VALUES (?, ?, ?, ?, ?)
        """, (now_str, input_filename, annotated_filename, json.dumps(detected_counts), total_count))
        scan_id = cur.lastrowid
        conn.commit()
        conn.close()
        return scan_id, now_str

    @staticmethod
    def get_recent(limit=4):
        conn = get_db()
        rows = conn.execute(f"SELECT * FROM scans ORDER BY id DESC LIMIT {int(limit)}").fetchall()
        conn.close()
        return rows

    @staticmethod
    def learn_crop(product_id, filename):
        conn = get_db()
        conn.execute("INSERT INTO product_refs (product_id, filename) VALUES (?, ?)", (product_id, filename))
        conn.commit()
        conn.close()

    @staticmethod
    def sync_counts(counts_map, sync_mode="update"):
        conn = get_db()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updated = []
        for pid, count in counts_map.items():
            row = conn.execute("SELECT name, quantity FROM products WHERE id = ?", (pid,)).fetchone()
            if row:
                old_qty = row["quantity"]
                new_qty = old_qty + count if sync_mode == "add" else count
                conn.execute("UPDATE products SET quantity = ?, last_updated = ? WHERE id = ?", (new_qty, now_str, pid))
                updated.append(f"{row['name']} ({old_qty} → {new_qty})")
        conn.commit()
        conn.close()
        return updated
