"""INVENTO AI Database Service.
Implements a deep database seam supporting both Supabase (PostgreSQL) and SQLite fallback.
"""
import os
import sqlite3
import json
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash
import backend.config as config
from backend.services.barcode import make_internal_ean13

try:
    from backend.seed_data.foods import FOODS
except ImportError:
    try:
        from seed_data.foods import FOODS
    except ImportError:
        FOODS = []


class CursorWrapper:
    """Wraps cursor to provide lastrowid and uniform behavior across drivers."""
    def __init__(self, cur, is_postgres=False):
        self._cur = cur
        self.is_postgres = is_postgres

    def __iter__(self):
        return iter(self._cur)

    @property
    def lastrowid(self):
        if self.is_postgres:
            return getattr(self._cur, 'lastrowid', None)
        return self._cur.lastrowid

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def execute(self, sql, params=None):
        if params is None:
            params = ()
        if self.is_postgres:
            sql = sql.replace("?", "%s")
        return self._cur.execute(sql, params)


class DBConnectionWrapper:
    """Wraps an SQLite or PostgreSQL connection to provide uniform interface and row dict access."""
    def __init__(self, conn, is_postgres=False):
        self.conn = conn
        self.is_postgres = is_postgres

    def cursor(self):
        return CursorWrapper(self.conn.cursor(), self.is_postgres)

    def execute(self, sql, params=None):
        if params is None:
            params = ()
        if self.is_postgres:
            sql = sql.replace("?", "%s")
            cur = self.conn.cursor()
            cur.execute(sql, params)
            return CursorWrapper(cur, is_postgres=True)
        return self.conn.execute(sql, params)

    def commit(self):
        return self.conn.commit()

    def rollback(self):
        return self.conn.rollback()

    def close(self):
        return self.conn.close()


def get_db():
    """Retrieve active database connection. Uses Supabase if DATABASE_URL is configured,
    otherwise falls back smoothly to local SQLite."""
    # When testing or INVENTO_DB explicitly specified, use that SQLite path
    if os.environ.get("INVENTO_DB"):
        config.ensure_directories()
        conn = sqlite3.connect(os.environ["INVENTO_DB"])
        conn.row_factory = sqlite3.Row
        return DBConnectionWrapper(conn, is_postgres=False)

    db_url = config.DATABASE_URL
    if db_url and db_url.startswith(("postgres://", "postgresql://")):
        try:
            import psycopg2
            from psycopg2.extras import DictCursor
            conn = psycopg2.connect(db_url, cursor_factory=DictCursor, connect_timeout=8)
            return DBConnectionWrapper(conn, is_postgres=True)
        except Exception as e:
            print(f"[DB Warning] Could not connect via DATABASE_URL ({e}). Falling back to local SQLite.")

    # Local SQLite fallback
    config.ensure_directories()
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return DBConnectionWrapper(conn, is_postgres=False)


def init_db():
    """Initializes schema and pre-seeds catalog in database."""
    config.ensure_directories()
    conn = get_db()
    
    # If connected to Supabase PostgreSQL, tables and seed data are already pushed!
    if conn.is_postgres:
        print("[DB] Connected to Supabase PostgreSQL cloud instance.")
        conn.close()
        return

    # For local SQLite fallback:
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'admin',
            email TEXT,
            name TEXT
        )
    """)

    cursor.execute("PRAGMA table_info(users)")
    user_cols = [c[1] for c in cursor.fetchall()]
    if "email" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
    if "name" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN name TEXT")

    # Products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            reorder_level INTEGER NOT NULL DEFAULT 5,
            price REAL NOT NULL DEFAULT 0.0,
            description TEXT,
            expiry_date TEXT,
            last_updated TEXT,
            image TEXT,
            barcode TEXT,
            gst_rate REAL NOT NULL DEFAULT 5
        )
    """)

    cursor.execute("PRAGMA table_info(products)")
    columns = [col[1] for col in cursor.fetchall()]
    if "expiry_date" not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN expiry_date TEXT")
    if "image" not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN image TEXT")
    if "barcode" not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN barcode TEXT")
    if "gst_rate" not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN gst_rate REAL NOT NULL DEFAULT 5")

    # Billing tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_no TEXT UNIQUE NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT,
            payment_method TEXT NOT NULL,
            total REAL NOT NULL,
            cashier TEXT,
            created_at TEXT NOT NULL,
            subtotal REAL NOT NULL DEFAULT 0,
            discount_type TEXT DEFAULT 'percent',
            discount_value REAL DEFAULT 0,
            discount_amount REAL DEFAULT 0,
            gst_amount REAL DEFAULT 0,
            delivery_fee REAL DEFAULT 0,
            order_type TEXT DEFAULT 'store',
            address TEXT DEFAULT '',
            payment_ref TEXT DEFAULT ''
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bill_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER NOT NULL,
            product_id INTEGER,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            subtotal REAL NOT NULL,
            gst_rate REAL DEFAULT 0,
            gst_amount REAL DEFAULT 0,
            discount_amount REAL DEFAULT 0,
            FOREIGN KEY (bill_id) REFERENCES bills(id)
        )
    """)

    # Scans table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            original_image TEXT NOT NULL,
            annotated_image TEXT NOT NULL,
            detected_counts TEXT NOT NULL,
            total_items INTEGER NOT NULL
        )
    """)

    cursor.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS product_refs (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER NOT NULL, filename TEXT NOT NULL)")

    # Seed Role Users if not exists
    seed_users = [
        ('admin', 'admin@invento.ai', 'admin123', 'admin', 'Store Administrator'),
        ('stock', 'stock@invento.ai', 'stock123', 'inventory_manager', 'Sarah Chen (Inventory Lead)'),
        ('cashier', 'cashier@invento.ai', 'cashier123', 'cashier', 'Alex Rivera (Head Cashier)'),
        ('customer', 'customer@invento.ai', 'customer123', 'customer', 'Rahul Verma (Customer)')
    ]
    for uname, uemail, upwd, urole, ufullname in seed_users:
        row = cursor.execute("SELECT id FROM users WHERE username = ?", (uname,)).fetchone()
        if not row:
            cursor.execute("INSERT INTO users (username, password, role, email, name) VALUES (?, ?, ?, ?, ?)",
                           (uname, generate_password_hash(upwd, method='pbkdf2:sha256'), urole, uemail, ufullname))
        else:
            cursor.execute("UPDATE users SET email = COALESCE(email, ?), name = COALESCE(name, ?), role = ? WHERE id = ?",
                           (uemail, ufullname, urole, row["id"]))

    # Seed initial sample products if table is empty
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        today = date.today()
        sample_products = [
            ("Coca Cola", "Beverages", 18, 10, 40.0, "500ml chilled soft drink bottle", (today + timedelta(days=90)).strftime("%Y-%m-%d")),
            ("Pepsi", "Beverages", 12, 10, 38.0, "500ml can", (today + timedelta(days=120)).strftime("%Y-%m-%d")),
            ("Milk", "Dairy", 3, 5, 30.0, "1L fresh cow milk carton", (today - timedelta(days=2)).strftime("%Y-%m-%d")),
            ("Biscuits", "Snacks", 4, 8, 30.0, "Crispy whole wheat biscuit pack", (today + timedelta(days=45)).strftime("%Y-%m-%d")),
            ("Soap", "Personal Care", 2, 5, 35.0, "Gentle skin cleanser bar", (today + timedelta(days=365)).strftime("%Y-%m-%d")),
            ("Shampoo", "Personal Care", 12, 6, 120.0, "200ml anti-dandruff shampoo", (today + timedelta(days=400)).strftime("%Y-%m-%d")),
            ("Fresh Apple", "Produce", 15, 6, 25.0, "Crisp red apple", (today + timedelta(days=3)).strftime("%Y-%m-%d")),
            ("Instant Noodles", "Snacks", 1, 5, 20.0, "Quick spicy noodle pack", (today + timedelta(days=5)).strftime("%Y-%m-%d"))
        ]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for name, cat, qty, reorder, price, desc, exp in sample_products:
            cursor.execute("""
                INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, cat, qty, reorder, price, desc, exp, now))

    # Set image & GST presets for sample products
    for cat, rate in config.GST_DEFAULTS.items():
        cursor.execute("UPDATE products SET gst_rate = ? WHERE category = ? AND (gst_rate IS NULL OR gst_rate = 5)", (rate, cat))
    for pname, fname in config.SEED_IMAGES.items():
        cursor.execute("UPDATE products SET image = ? WHERE name = ? AND (image IS NULL OR image = '')", ("img/products/" + fname, pname))

    # Seed food catalogue if meta flag missing
    cursor.execute("SELECT 1 FROM meta WHERE key = 'foods_seeded_v1'")
    if not cursor.fetchone():
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for name, cat, price, gst, shelf_days, desc in FOODS:
            if cursor.execute("SELECT 1 FROM products WHERE LOWER(name) = LOWER(?)", (name,)).fetchone():
                continue
            expiry = (date.today() + timedelta(days=shelf_days)).strftime("%Y-%m-%d")
            cursor.execute("""
                INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, gst_rate)
                VALUES (?, ?, 10, 5, ?, ?, ?, ?, ?)
            """, (name, cat, price, desc, expiry, now, gst))
        cursor.execute("INSERT INTO meta (key, value) VALUES ('foods_seeded_v1', '1')")

    # Barcodes
    for row in cursor.execute("SELECT id FROM products WHERE barcode IS NULL OR barcode = ''").fetchall():
        cursor.execute("UPDATE products SET barcode = ? WHERE id = ?", (make_internal_ean13(row["id"]), row["id"]))
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode) WHERE barcode IS NOT NULL AND barcode != ''")

    conn.commit()
    conn.close()
