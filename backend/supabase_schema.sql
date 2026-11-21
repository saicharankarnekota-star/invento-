-- ==============================================================================
-- INVENTO AI — Supabase (PostgreSQL) Database Initialization Script
-- ==============================================================================
-- Run this in your Supabase Project:
-- Dashboard -> SQL Editor -> New query -> Paste this script -> Click "Run"
-- ==============================================================================

-- Compatibility Helpers
CREATE OR REPLACE FUNCTION _group_concat_trans(state text, val text, delim text)
RETURNS text LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE WHEN state IS NULL THEN val ELSE state || delim || val END;
$$;

CREATE OR REPLACE AGGREGATE group_concat(text, text) (
    SFUNC = _group_concat_trans,
    STYPE = text
);

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

-- Seed Default Role Users
INSERT INTO users (username, password, role, email, name)
VALUES 
  ('admin', 'pbkdf2:sha256:1000000$vLdYfrwGfYs3Zbon$eac23748a980a3a7d683d97c679411b879e6a3fde015e2b7e308016e1831da68', 'admin', 'admin@invento.ai', 'Store Administrator'),
  ('stock', 'pbkdf2:sha256:1000000$vLdYfrwGfYs3Zbon$eac23748a980a3a7d683d97c679411b879e6a3fde015e2b7e308016e1831da68', 'inventory_manager', 'stock@invento.ai', 'Sarah Chen (Inventory Lead)'),
  ('cashier', 'pbkdf2:sha256:1000000$vLdYfrwGfYs3Zbon$eac23748a980a3a7d683d97c679411b879e6a3fde015e2b7e308016e1831da68', 'cashier', 'cashier@invento.ai', 'Alex Rivera (Head Cashier)')
ON CONFLICT (username) DO UPDATE 
SET role = EXCLUDED.role, email = EXCLUDED.email, name = EXCLUDED.name;


-- Seed Core Sample Products

INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate, image) VALUES ('Coca Cola', 'Beverages', 18, 10, 40.00, '500ml chilled soft drink bottle', '2027-02-11', '2026-11-13 10:00:00', '2000000000015', 12.00, 'img/products/coca-cola.svg');
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate, image) VALUES ('Pepsi', 'Beverages', 12, 10, 38.00, '500ml can', '2027-03-13', '2026-11-13 10:00:00', '2000000000022', 12.00, 'img/products/pepsi.svg');
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate, image) VALUES ('Milk', 'Dairy', 3, 5, 30.00, '1L fresh cow milk carton', '2026-11-11', '2026-11-13 10:00:00', '2000000000039', 0.00, 'img/products/milk.svg');
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate, image) VALUES ('Biscuits', 'Snacks', 4, 8, 30.00, 'Crispy whole wheat biscuit pack', '2026-12-28', '2026-11-13 10:00:00', '2000000000046', 12.00, 'img/products/biscuits.svg');
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate, image) VALUES ('Soap', 'Personal Care', 2, 5, 35.00, 'Gentle skin cleanser bar', '2027-11-13', '2026-11-13 10:00:00', '2000000000053', 18.00, 'img/products/soap.svg');
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate, image) VALUES ('Shampoo', 'Personal Care', 12, 6, 120.00, '200ml anti-dandruff shampoo', '2027-12-18', '2026-11-13 10:00:00', '2000000000060', 18.00, 'img/products/shampoo.svg');
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate, image) VALUES ('Fresh Apple', 'Produce', 15, 6, 25.00, 'Crisp red apple', '2026-11-16', '2026-11-13 10:00:00', '2000000000077', 0.00, 'img/products/apple.svg');
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate, image) VALUES ('Instant Noodles', 'Snacks', 1, 5, 20.00, 'Quick spicy noodle pack', '2026-11-18', '2026-11-13 10:00:00', '2000000000084', 12.00, 'img/products/noodles.svg');

-- Seed Food Catalogue (133 items)

INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Sprite', 'Beverages', 10, 5, 40.00, 'Lemon-lime soft drink 500ml', '2027-03-13', '2026-11-13 10:00:00', '2000000000091', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Fanta Orange', 'Beverages', 10, 5, 40.00, 'Orange soft drink 500ml', '2027-03-13', '2026-11-13 10:00:00', '2000000000107', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Thums Up', 'Beverages', 10, 5, 40.00, 'Strong cola soft drink 500ml', '2027-03-13', '2026-11-13 10:00:00', '2000000000114', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('7UP', 'Beverages', 10, 5, 38.00, 'Lemon-lime soft drink 500ml', '2027-03-13', '2026-11-13 10:00:00', '2000000000121', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Mountain Dew', 'Beverages', 10, 5, 38.00, 'Citrus soft drink 500ml', '2027-03-13', '2026-11-13 10:00:00', '2000000000138', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Limca', 'Beverages', 10, 5, 38.00, 'Lemon soft drink 500ml', '2027-03-13', '2026-11-13 10:00:00', '2000000000145', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Maaza Mango Drink', 'Beverages', 10, 5, 25.00, 'Mango fruit drink 250ml', '2027-05-12', '2026-11-13 10:00:00', '2000000000152', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Frooti Mango Drink', 'Beverages', 10, 5, 20.00, 'Mango fruit drink 200ml', '2027-05-12', '2026-11-13 10:00:00', '2000000000169', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Real Fruit Juice Orange', 'Beverages', 10, 5, 110.00, 'Orange juice 1L', '2027-05-12', '2026-11-13 10:00:00', '2000000000176', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Tropicana Mixed Fruit Juice', 'Beverages', 10, 5, 115.00, 'Mixed fruit juice 1L', '2027-05-12', '2026-11-13 10:00:00', '2000000000183', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Red Bull Energy Drink', 'Beverages', 10, 5, 125.00, 'Energy drink 250ml can', '2027-11-13', '2026-11-13 10:00:00', '2000000000190', 28.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Bisleri Mineral Water', 'Beverages', 10, 5, 20.00, 'Packaged drinking water 1L', '2027-11-13', '2026-11-13 10:00:00', '2000000000206', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Kinley Soda', 'Beverages', 10, 5, 20.00, 'Club soda 750ml', '2027-11-13', '2026-11-13 10:00:00', '2000000000213', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Tata Tea Gold', 'Beverages', 10, 5, 135.00, 'Tea leaves 250g', '2027-11-13', '2026-11-13 10:00:00', '2000000000220', 5.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Red Label Tea', 'Beverages', 10, 5, 120.00, 'Tea leaves 250g', '2027-11-13', '2026-11-13 10:00:00', '2000000000237', 5.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Nescafe Classic Coffee', 'Beverages', 10, 5, 190.00, 'Instant coffee jar 100g', '2028-05-06', '2026-11-13 10:00:00', '2000000000244', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Bru Instant Coffee', 'Beverages', 10, 5, 175.00, 'Instant coffee jar 100g', '2028-05-06', '2026-11-13 10:00:00', '2000000000251', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Bournvita', 'Beverages', 10, 5, 245.00, 'Health drink powder 500g', '2027-11-13', '2026-11-13 10:00:00', '2000000000268', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Horlicks', 'Beverages', 10, 5, 260.00, 'Malted health drink 500g', '2027-11-13', '2026-11-13 10:00:00', '2000000000275', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Coconut Water', 'Beverages', 10, 5, 40.00, 'Tender coconut water 200ml', '2027-03-13', '2026-11-13 10:00:00', '2000000000282', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Amul Butter', 'Dairy', 10, 5, 58.00, 'Salted butter 100g', '2027-05-12', '2026-11-13 10:00:00', '2000000000299', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Amul Cheese Slices', 'Dairy', 10, 5, 135.00, 'Processed cheese slices 200g', '2027-04-12', '2026-11-13 10:00:00', '2000000000305', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Amul Cheese Cube', 'Dairy', 10, 5, 130.00, 'Processed cheese cubes 200g', '2027-04-12', '2026-11-13 10:00:00', '2000000000312', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Paneer', 'Dairy', 10, 5, 95.00, 'Fresh paneer 200g', '2026-11-28', '2026-11-13 10:00:00', '2000000000329', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Curd', 'Dairy', 10, 5, 35.00, 'Fresh set curd 400g', '2026-11-20', '2026-11-13 10:00:00', '2000000000336', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Amul Masti Buttermilk', 'Dairy', 10, 5, 15.00, 'Spiced buttermilk 200ml', '2026-12-13', '2026-11-13 10:00:00', '2000000000343', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Amul Lassi', 'Dairy', 10, 5, 25.00, 'Sweet lassi 200ml', '2026-12-28', '2026-11-13 10:00:00', '2000000000350', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Flavoured Milk Chocolate', 'Dairy', 10, 5, 30.00, 'Chocolate milk 200ml', '2027-01-12', '2026-11-13 10:00:00', '2000000000367', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Mother Dairy Ghee', 'Dairy', 10, 5, 330.00, 'Cow ghee 500ml', '2027-11-13', '2026-11-13 10:00:00', '2000000000374', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Fruit Yogurt Strawberry', 'Dairy', 10, 5, 30.00, 'Strawberry yogurt cup 100g', '2026-12-04', '2026-11-13 10:00:00', '2000000000381', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Cream Cheese Spread', 'Dairy', 10, 5, 120.00, 'Cheese spread 180g', '2027-03-13', '2026-11-13 10:00:00', '2000000000398', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Eggs (Tray of 6)', 'Dairy', 10, 5, 48.00, 'Farm eggs, 6 pieces', '2026-11-27', '2026-11-13 10:00:00', '2000000000404', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Lays Classic Salted', 'Snacks', 10, 5, 20.00, 'Potato chips 52g', '2027-02-11', '2026-11-13 10:00:00', '2000000000411', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Lays Magic Masala', 'Snacks', 10, 5, 20.00, 'Spicy potato chips 52g', '2027-02-11', '2026-11-13 10:00:00', '2000000000428', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Kurkure Masala Munch', 'Snacks', 10, 5, 20.00, 'Corn puff snack 90g', '2027-02-11', '2026-11-13 10:00:00', '2000000000435', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Bingo Mad Angles', 'Snacks', 10, 5, 20.00, 'Triangle chips 66g', '2027-02-11', '2026-11-13 10:00:00', '2000000000442', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Doritos Nacho Cheese', 'Snacks', 10, 5, 20.00, 'Tortilla chips 44g', '2027-02-11', '2026-11-13 10:00:00', '2000000000459', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Haldiram''s Aloo Bhujia', 'Snacks', 10, 5, 55.00, 'Fried potato noodles snack 200g', '2027-03-13', '2026-11-13 10:00:00', '2000000000466', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Haldiram''s Moong Dal', 'Snacks', 10, 5, 45.00, 'Fried moong dal snack 150g', '2027-03-13', '2026-11-13 10:00:00', '2000000000473', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Haldiram''s Navratan Mixture', 'Snacks', 10, 5, 55.00, 'Namkeen mixture 200g', '2027-03-13', '2026-11-13 10:00:00', '2000000000480', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Salted Peanuts', 'Snacks', 10, 5, 30.00, 'Roasted salted peanuts 100g', '2027-03-13', '2026-11-13 10:00:00', '2000000000497', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Popcorn Butter', 'Snacks', 10, 5, 30.00, 'Ready-to-eat butter popcorn 60g', '2027-03-13', '2026-11-13 10:00:00', '2000000000503', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Banana Chips', 'Snacks', 10, 5, 40.00, 'Kerala banana chips 100g', '2027-02-11', '2026-11-13 10:00:00', '2000000000510', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Murukku', 'Snacks', 10, 5, 45.00, 'South Indian rice snack 150g', '2027-01-12', '2026-11-13 10:00:00', '2000000000527', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Papad', 'Snacks', 10, 5, 40.00, 'Urad dal papad 200g', '2027-05-12', '2026-11-13 10:00:00', '2000000000534', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Cream Biscuit Orange', 'Snacks', 10, 5, 20.00, 'Orange cream sandwich biscuits 100g', '2027-05-12', '2026-11-13 10:00:00', '2000000000541', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Parle-G Biscuits', 'Bakery', 10, 5, 10.00, 'Glucose biscuits 56g', '2027-05-12', '2026-11-13 10:00:00', '2000000000558', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Good Day Cashew Cookies', 'Bakery', 10, 5, 30.00, 'Cashew butter cookies 100g', '2027-05-12', '2026-11-13 10:00:00', '2000000000565', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Marie Gold Biscuits', 'Bakery', 10, 5, 30.00, 'Tea-time marie biscuits 250g', '2027-05-12', '2026-11-13 10:00:00', '2000000000572', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Oreo Chocolate Cream Biscuits', 'Bakery', 10, 5, 30.00, 'Chocolate sandwich biscuits 120g', '2027-05-12', '2026-11-13 10:00:00', '2000000000589', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Hide & Seek Chocolate Chip Cookies', 'Bakery', 10, 5, 35.00, 'Choco chip cookies 100g', '2027-05-12', '2026-11-13 10:00:00', '2000000000596', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Digestive Biscuits', 'Bakery', 10, 5, 70.00, 'Whole wheat digestive biscuits 250g', '2027-05-12', '2026-11-13 10:00:00', '2000000000602', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Rusk', 'Bakery', 10, 5, 40.00, 'Crispy toast rusk 200g', '2027-03-13', '2026-11-13 10:00:00', '2000000000619', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('White Bread', 'Bakery', 10, 5, 40.00, 'Sliced white bread 400g', '2026-11-17', '2026-11-13 10:00:00', '2000000000626', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Brown Bread', 'Bakery', 10, 5, 50.00, 'Whole wheat bread 400g', '2026-11-17', '2026-11-13 10:00:00', '2000000000633', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Pav Buns', 'Bakery', 10, 5, 30.00, 'Soft pav buns, pack of 6', '2026-11-16', '2026-11-13 10:00:00', '2000000000640', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Burger Buns', 'Bakery', 10, 5, 35.00, 'Burger buns, pack of 4', '2026-11-16', '2026-11-13 10:00:00', '2000000000657', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Chocolate Cake Slice', 'Bakery', 10, 5, 35.00, 'Packaged chocolate cake 60g', '2026-11-23', '2026-11-13 10:00:00', '2000000000664', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Veg Puff', 'Bakery', 10, 5, 20.00, 'Freshly baked veg puff', '2026-11-15', '2026-11-13 10:00:00', '2000000000671', 5.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Maggi Masala Noodles', 'Instant Food', 10, 5, 14.00, '2-minute masala noodles 70g', '2027-08-10', '2026-11-13 10:00:00', '2000000000688', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Yippee Noodles', 'Instant Food', 10, 5, 14.00, 'Magic masala noodles 70g', '2027-08-10', '2026-11-13 10:00:00', '2000000000695', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Top Ramen Curry Noodles', 'Instant Food', 10, 5, 14.00, 'Curry noodles 70g', '2027-08-10', '2026-11-13 10:00:00', '2000000000701', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Cup Noodles Veg', 'Instant Food', 10, 5, 45.00, 'Instant cup noodles 70g', '2027-08-10', '2026-11-13 10:00:00', '2000000000718', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Pasta Macaroni', 'Instant Food', 10, 5, 35.00, 'Macaroni pasta 200g', '2027-11-13', '2026-11-13 10:00:00', '2000000000725', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Poha', 'Instant Food', 10, 5, 40.00, 'Flattened rice 500g', '2027-08-10', '2026-11-13 10:00:00', '2000000000732', 5.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Upma Mix', 'Instant Food', 10, 5, 60.00, 'Instant upma mix 200g', '2027-08-10', '2026-11-13 10:00:00', '2000000000749', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Idli Dosa Batter', 'Instant Food', 10, 5, 55.00, 'Ready idli/dosa batter 500g', '2026-11-17', '2026-11-13 10:00:00', '2000000000756', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Corn Flakes', 'Instant Food', 10, 5, 190.00, 'Breakfast corn flakes 475g', '2027-08-10', '2026-11-13 10:00:00', '2000000000763', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Chocos', 'Instant Food', 10, 5, 175.00, 'Chocolate breakfast cereal 375g', '2027-08-10', '2026-11-13 10:00:00', '2000000000770', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Rolled Oats', 'Instant Food', 10, 5, 110.00, 'Quick-cook oats 500g', '2027-08-10', '2026-11-13 10:00:00', '2000000000787', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Muesli', 'Instant Food', 10, 5, 280.00, 'Fruit & nut muesli 500g', '2027-08-10', '2026-11-13 10:00:00', '2000000000794', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Basmati Rice', 'Staples', 10, 5, 120.00, 'Long grain basmati rice 1kg', '2027-11-13', '2026-11-13 10:00:00', '2000000000800', 5.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Sona Masoori Rice', 'Staples', 10, 5, 65.00, 'Daily-use rice 1kg', '2027-11-13', '2026-11-13 10:00:00', '2000000000817', 5.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Wheat Flour (Atta)', 'Staples', 10, 5, 55.00, 'Whole wheat atta 1kg', '2027-05-12', '2026-11-13 10:00:00', '2000000000824', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Maida', 'Staples', 10, 5, 45.00, 'Refined wheat flour 1kg', '2027-05-12', '2026-11-13 10:00:00', '2000000000831', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Besan', 'Staples', 10, 5, 80.00, 'Gram flour 500g', '2027-05-12', '2026-11-13 10:00:00', '2000000000848', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Toor Dal', 'Staples', 10, 5, 165.00, 'Split pigeon peas 1kg', '2027-11-13', '2026-11-13 10:00:00', '2000000000855', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Moong Dal', 'Staples', 10, 5, 130.00, 'Split green gram 1kg', '2027-11-13', '2026-11-13 10:00:00', '2000000000862', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Chana Dal', 'Staples', 10, 5, 100.00, 'Split chickpeas 1kg', '2027-11-13', '2026-11-13 10:00:00', '2000000000879', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Urad Dal', 'Staples', 10, 5, 140.00, 'Split black gram 1kg', '2027-11-13', '2026-11-13 10:00:00', '2000000000886', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Rajma', 'Staples', 10, 5, 150.00, 'Red kidney beans 500g', '2027-11-13', '2026-11-13 10:00:00', '2000000000893', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Sugar', 'Staples', 10, 5, 48.00, 'Refined sugar 1kg', '2028-05-06', '2026-11-13 10:00:00', '2000000000909', 5.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Iodised Salt', 'Staples', 10, 5, 28.00, 'Tata salt 1kg', '2028-11-12', '2026-11-13 10:00:00', '2000000000916', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Jaggery', 'Staples', 10, 5, 70.00, 'Organic jaggery 500g', '2027-11-13', '2026-11-13 10:00:00', '2000000000923', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Sunflower Oil', 'Staples', 10, 5, 150.00, 'Refined sunflower oil 1L', '2027-08-10', '2026-11-13 10:00:00', '2000000000930', 5.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Groundnut Oil', 'Staples', 10, 5, 210.00, 'Cold-pressed groundnut oil 1L', '2027-08-10', '2026-11-13 10:00:00', '2000000000947', 5.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Mustard Oil', 'Staples', 10, 5, 170.00, 'Kachi ghani mustard oil 1L', '2027-08-10', '2026-11-13 10:00:00', '2000000000954', 5.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Turmeric Powder', 'Spices & Sauces', 10, 5, 45.00, 'Haldi powder 100g', '2027-11-13', '2026-11-13 10:00:00', '2000000000961', 5.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Red Chilli Powder', 'Spices & Sauces', 10, 5, 60.00, 'Spicy chilli powder 100g', '2027-11-13', '2026-11-13 10:00:00', '2000000000978', 5.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Coriander Powder', 'Spices & Sauces', 10, 5, 40.00, 'Dhania powder 100g', '2027-11-13', '2026-11-13 10:00:00', '2000000000985', 5.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Garam Masala', 'Spices & Sauces', 10, 5, 55.00, 'Blended spice mix 100g', '2027-11-13', '2026-11-13 10:00:00', '2000000000992', 5.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Cumin Seeds', 'Spices & Sauces', 10, 5, 60.00, 'Jeera 100g', '2027-11-13', '2026-11-13 10:00:00', '2000000001005', 5.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Mustard Seeds', 'Spices & Sauces', 10, 5, 25.00, 'Rai 100g', '2027-11-13', '2026-11-13 10:00:00', '2000000001012', 5.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Black Pepper', 'Spices & Sauces', 10, 5, 80.00, 'Whole black pepper 50g', '2027-11-13', '2026-11-13 10:00:00', '2000000001029', 5.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Tomato Ketchup', 'Spices & Sauces', 10, 5, 95.00, 'Tomato sauce 500g', '2027-11-13', '2026-11-13 10:00:00', '2000000001036', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Mayonnaise', 'Spices & Sauces', 10, 5, 85.00, 'Eggless mayonnaise 250g', '2027-05-12', '2026-11-13 10:00:00', '2000000001043', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Soy Sauce', 'Spices & Sauces', 10, 5, 45.00, 'Dark soy sauce 200ml', '2027-11-13', '2026-11-13 10:00:00', '2000000001050', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Schezwan Chutney', 'Spices & Sauces', 10, 5, 70.00, 'Schezwan sauce 250g', '2027-08-10', '2026-11-13 10:00:00', '2000000001067', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Mixed Fruit Jam', 'Spices & Sauces', 10, 5, 120.00, 'Fruit jam 500g', '2027-11-13', '2026-11-13 10:00:00', '2000000001074', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Peanut Butter', 'Spices & Sauces', 10, 5, 180.00, 'Creamy peanut butter 340g', '2027-08-10', '2026-11-13 10:00:00', '2000000001081', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Mango Pickle', 'Spices & Sauces', 10, 5, 85.00, 'Avakaya mango pickle 300g', '2027-11-13', '2026-11-13 10:00:00', '2000000001098', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Honey', 'Spices & Sauces', 10, 5, 185.00, 'Pure honey 500g', '2028-05-06', '2026-11-13 10:00:00', '2000000001104', 5.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Dairy Milk Chocolate', 'Sweets & Chocolates', 10, 5, 40.00, 'Milk chocolate bar 50g', '2027-08-10', '2026-11-13 10:00:00', '2000000001111', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('KitKat', 'Sweets & Chocolates', 10, 5, 30.00, 'Wafer chocolate bar', '2027-08-10', '2026-11-13 10:00:00', '2000000001128', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('5 Star Chocolate', 'Sweets & Chocolates', 10, 5, 10.00, 'Caramel chocolate bar', '2027-05-12', '2026-11-13 10:00:00', '2000000001135', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Munch Chocolate', 'Sweets & Chocolates', 10, 5, 10.00, 'Crunchy wafer chocolate', '2027-05-12', '2026-11-13 10:00:00', '2000000001142', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Snickers', 'Sweets & Chocolates', 10, 5, 50.00, 'Peanut caramel chocolate bar', '2027-08-10', '2026-11-13 10:00:00', '2000000001159', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Mint Candy', 'Sweets & Chocolates', 10, 5, 5.00, 'Mint candy sachet', '2027-11-13', '2026-11-13 10:00:00', '2000000001166', 18.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Gulab Jamun Tin', 'Sweets & Chocolates', 10, 5, 140.00, 'Ready-to-eat gulab jamun 1kg tin', '2027-05-12', '2026-11-13 10:00:00', '2000000001173', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Soan Papdi', 'Sweets & Chocolates', 10, 5, 90.00, 'Flaky sweet 250g', '2027-01-12', '2026-11-13 10:00:00', '2000000001180', 5.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Almonds', 'Dry Fruits', 10, 5, 190.00, 'California almonds 250g', '2027-08-10', '2026-11-13 10:00:00', '2000000001197', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Cashew Nuts', 'Dry Fruits', 10, 5, 260.00, 'Whole cashews 250g', '2027-08-10', '2026-11-13 10:00:00', '2000000001203', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Raisins', 'Dry Fruits', 10, 5, 80.00, 'Seedless raisins 250g', '2027-08-10', '2026-11-13 10:00:00', '2000000001210', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Dates', 'Dry Fruits', 10, 5, 120.00, 'Soft dates 500g', '2027-08-10', '2026-11-13 10:00:00', '2000000001227', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Walnuts', 'Dry Fruits', 10, 5, 230.00, 'Walnut kernels 250g', '2027-08-10', '2026-11-13 10:00:00', '2000000001234', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Pistachios', 'Dry Fruits', 10, 5, 320.00, 'Roasted salted pistachios 250g', '2027-08-10', '2026-11-13 10:00:00', '2000000001241', 12.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Banana', 'Produce', 10, 5, 50.00, 'Robusta bananas, 1 dozen', '2026-11-17', '2026-11-13 10:00:00', '2000000001258', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Orange', 'Produce', 10, 5, 80.00, 'Nagpur oranges 1kg', '2026-11-20', '2026-11-13 10:00:00', '2000000001265', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Mango', 'Produce', 10, 5, 120.00, 'Seasonal mangoes 1kg', '2026-11-18', '2026-11-13 10:00:00', '2000000001272', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Grapes', 'Produce', 10, 5, 90.00, 'Seedless grapes 500g', '2026-11-19', '2026-11-13 10:00:00', '2000000001289', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Pomegranate', 'Produce', 10, 5, 150.00, 'Pomegranate 1kg', '2026-11-21', '2026-11-13 10:00:00', '2000000001296', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Watermelon', 'Produce', 10, 5, 40.00, 'Watermelon 1kg', '2026-11-19', '2026-11-13 10:00:00', '2000000001302', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Papaya', 'Produce', 10, 5, 45.00, 'Ripe papaya 1kg', '2026-11-18', '2026-11-13 10:00:00', '2000000001319', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Tomato', 'Produce', 10, 5, 30.00, 'Fresh tomatoes 1kg', '2026-11-18', '2026-11-13 10:00:00', '2000000001326', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Onion', 'Produce', 10, 5, 35.00, 'Red onions 1kg', '2026-12-03', '2026-11-13 10:00:00', '2000000001333', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Potato', 'Produce', 10, 5, 30.00, 'Potatoes 1kg', '2026-12-03', '2026-11-13 10:00:00', '2000000001340', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Carrot', 'Produce', 10, 5, 50.00, 'Carrots 1kg', '2026-11-23', '2026-11-13 10:00:00', '2000000001357', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Cucumber', 'Produce', 10, 5, 30.00, 'Cucumber 500g', '2026-11-20', '2026-11-13 10:00:00', '2000000001364', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Green Chilli', 'Produce', 10, 5, 20.00, 'Green chillies 100g', '2026-11-19', '2026-11-13 10:00:00', '2000000001371', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Coriander Leaves', 'Produce', 10, 5, 10.00, 'Fresh coriander bunch', '2026-11-16', '2026-11-13 10:00:00', '2000000001388', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Lemon', 'Produce', 10, 5, 20.00, 'Lemons, pack of 4', '2026-11-23', '2026-11-13 10:00:00', '2000000001395', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Spinach', 'Produce', 10, 5, 20.00, 'Fresh palak bunch', '2026-11-16', '2026-11-13 10:00:00', '2000000001401', 0.00);
INSERT INTO products (name, category, quantity, reorder_level, price, description, expiry_date, last_updated, barcode, gst_rate) VALUES ('Cauliflower', 'Produce', 10, 5, 40.00, 'Cauliflower 1 piece', '2026-11-19', '2026-11-13 10:00:00', '2000000001418', 0.00);

INSERT INTO meta (key, value) VALUES ('foods_seeded_v1', '1') ON CONFLICT (key) DO NOTHING;
