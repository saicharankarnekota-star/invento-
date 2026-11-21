import sys
from seed_foods import FOODS
from datetime import date, timedelta

def check_digit(first12):
    s = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(first12))
    return str((10 - s % 10) % 10)

def make_ean13(seq):
    body = "200" + str(int(seq)).zfill(9)
    return body + check_digit(body)

# Default admin password hash for "admin123"
admin_hash = "scrypt:32768:8:1$7tS5v9b1r2P4q0yZ$8c1995874c7608ad8cfec7816bc8d24669f52f5df5cf7cba14d7bfa5db2f4422e865f121d1544b611e967a5bb01d51fe2daebc77d543118cf9d2dfaa41beecba"

sql = []
sql.append("""-- ==============================================================================
-- INVENTO AI — Supabase (PostgreSQL) Database Initialization Script
-- ==============================================================================
-- Run this in your Supabase Project:
-- Dashboard -> SQL Editor -> New query -> Paste this script -> Click "Run"
-- ==============================================================================

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'admin',
    email VARCHAR(150),
    name VARCHAR(150)
);

-- 2. Products Table
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(100) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    reorder_level INTEGER NOT NULL DEFAULT 5,
    price NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    description TEXT,
    expiry_date VARCHAR(20),
    last_updated VARCHAR(30),
    image VARCHAR(255),
    barcode VARCHAR(50),
    gst_rate NUMERIC(5, 2) NOT NULL DEFAULT 5.00
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode) WHERE barcode IS NOT NULL AND barcode != '';
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);

-- 3. Scans Table
CREATE TABLE IF NOT EXISTS scans (
    id SERIAL PRIMARY KEY,
    timestamp VARCHAR(30) NOT NULL,
    original_image VARCHAR(255) NOT NULL,
    annotated_image VARCHAR(255) NOT NULL,
    detected_counts TEXT NOT NULL,
    total_items INTEGER NOT NULL
);

-- 4. Bills Table
CREATE TABLE IF NOT EXISTS bills (
    id SERIAL PRIMARY KEY,
    bill_no VARCHAR(100) UNIQUE NOT NULL,
    customer_name VARCHAR(150) NOT NULL,
    customer_phone VARCHAR(50),
    payment_method VARCHAR(50) NOT NULL,
    total NUMERIC(10, 2) NOT NULL,
    cashier VARCHAR(100),
    created_at VARCHAR(30) NOT NULL,
    subtotal NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    discount_type VARCHAR(20) DEFAULT 'percent',
    discount_value NUMERIC(10, 2) DEFAULT 0.00,
    discount_amount NUMERIC(10, 2) DEFAULT 0.00,
    gst_amount NUMERIC(10, 2) DEFAULT 0.00,
    delivery_fee NUMERIC(10, 2) DEFAULT 0.00,
    order_type VARCHAR(50) DEFAULT 'store',
    address TEXT DEFAULT '',
    payment_ref VARCHAR(255) DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_bills_created_at ON bills(created_at);

-- 5. Bill Items Table
CREATE TABLE IF NOT EXISTS bill_items (
    id SERIAL PRIMARY KEY,
    bill_id INTEGER NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    name VARCHAR(200) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    subtotal NUMERIC(10, 2) NOT NULL,
    gst_rate NUMERIC(5, 2) DEFAULT 0.00,
    gst_amount NUMERIC(10, 2) DEFAULT 0.00,
    discount_amount NUMERIC(10, 2) DEFAULT 0.00
);

-- 6. Meta Table
CREATE TABLE IF NOT EXISTS meta (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT
);

-- 7. Product References Table (for AI learned feature crops)
CREATE TABLE IF NOT EXISTS product_refs (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL
);

-- Seed Default Admin User (admin / admin123)
INSERT INTO users (username, password, role, email, name)
VALUES ('admin', '""" + admin_hash + """', 'admin', 'admin@invento.ai', 'Store Admin')
ON CONFLICT (username) DO NOTHING;
""")

today = date.today()
now_str = today.strftime("%Y-%m-%d 10:00:00")

# Sample core products
samples = [
    ("Coca Cola", "Beverages", 18, 10, 40.0, "500ml chilled soft drink bottle", (today + timedelta(days=90)).strftime("%Y-%m-%d"), 12.0, "img/products/coca-cola.svg"),
    ("Pepsi", "Beverages", 12, 10, 38.0, "500ml can", (today + timedelta(days=120)).strftime("%Y-%m-%d"), 12.0, "img/products/pepsi.svg"),
    ("Milk", "Dairy", 3, 5, 30.0, "1L fresh cow milk carton", (today - timedelta(days=2)).strftime("%Y-%m-%d"), 0.0, "img/products/milk.svg"),
    ("Biscuits", "Snacks", 4, 8, 30.0, "Crispy whole wheat biscuit pack", (today + timedelta(days=45)).strftime("%Y-%m-%d"), 12.0, "img/products/biscuits.svg"),
    ("Soap", "Personal Care", 2, 5, 35.0, "Gentle skin cleanser bar", (today + timedelta(days=365)).strftime("%Y-%m-%d"), 18.0, "img/products/soap.svg"),
    ("Shampoo", "Personal Care", 12, 6, 120.0, "200ml anti-dandruff shampoo", (today + timedelta(days=400)).strftime("%Y-%m-%d"), 18.0, "img/products/shampoo.svg"),
    ("Fresh Apple", "Produce", 15, 6, 25.0, "Crisp red apple", (today + timedelta(days=3)).strftime("%Y-%m-%d"), 0.0, "img/products/apple.svg"),
    ("Instant Noodles", "Snacks", 1, 5, 20.0, "Quick spicy noodle pack", (today + timedelta(days=5)).strftime("%Y-%m-%d"), 12.0, "img/products/noodles.svg"),
]

sql.append("\n-- Seed Core Sample Products\n")
prod_id = 1
for name, cat, qty, reorder, price, desc, exp, gst, img in samples:
    barcode = make_ean13(prod_id)
    esc_desc = desc.replace("'", "''")
    sql.append(f"INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate, image) VALUES ('{name}', '{cat}', {qty}, {reorder}, {price:.2f}, '{esc_desc}', '{exp}', '{now_str}', '{barcode}', {gst:.2f}, '{img}');")
    prod_id += 1

sql.append("\n-- Seed Food Catalogue (133 items)\n")
for name, cat, price, gst, shelf_days, desc in FOODS:
    barcode = make_ean13(prod_id)
    expiry = (today + timedelta(days=shelf_days)).strftime("%Y-%m-%d")
    esc_name = name.replace("'", "''")
    esc_desc = desc.replace("'", "''")
    sql.append(f"INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('{esc_name}', '{cat}', 10, 5, {price:.2f}, '{esc_desc}', '{expiry}', '{now_str}', '{barcode}', {gst:.2f});")
    prod_id += 1

sql.append("\nINSERT INTO meta (key, value) VALUES ('foods_seeded_v1', '1') ON CONFLICT (key) DO NOTHING;\n")

content = "\n".join(sql)
with open("database/supabase_schema.sql", "w") as f:
    f.write(content)
with open("backend/supabase_schema.sql", "w") as f:
    f.write(content)
print("Schema successfully generated in database/supabase_schema.sql and backend/supabase_schema.sql")
