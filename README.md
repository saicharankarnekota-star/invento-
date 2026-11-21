# INVENTO AI — Full Stack Smart Inventory Management & POS Platform

> **Modern Autonomous Retail Platform Pairing Computer Vision (YOLOv8 + OpenCV), Barcode Automation, POS Billing with Dynamic UPI QR, and Cloud Database (Supabase)**

---

## 📌 Architecture Overview

INVENTO AI is restructured into a clean, decoupled **Full Stack Application** with separate `frontend/` and `backend/` tiers, designed for zero-friction deployment to **Vercel** and seamless connection to **Supabase** (PostgreSQL).

```text
INVENTO-AI/
│
├── frontend/                     # Separated Presentation Tier (Vercel Edge Ready)
│   ├── index.html                # Store Landing & Navigation Portal
│   ├── login.html                # Authentication Portal
│   ├── register.html             # User Registration
│   ├── dashboard.html            # Real-time Metrics, Charts & Expiry Watchlist
│   ├── products.html             # Product Catalog & Category Filters
│   ├── add_product.html          # Add New Product Form (EAN-13 auto-generator)
│   ├── edit_product.html         # Edit Details & Custom Pack Barcodes
│   ├── scan.html                 # AI Shelf Scanner (Upload & Live Webcam)
│   ├── alerts.html               # Expiry & Out-of-Stock Action Center
│   ├── billing.html              # POS Terminal with Dynamic UPI QR
│   ├── bills.html                # Billing History & Records
│   ├── bill_detail.html          # Printable Tax Receipt & Invoice
│   ├── reports.html              # Valuation & Restock Reports
│   ├── _cart_dynamic.html        # Dynamic Cart Drawer
│   ├── _macros.html              # Jinja Helpers
│   ├── _auth_brand.html          # Brand Layout
│   ├── base.html                 # Global App Shell & Navigation
│   ├── css/
│   │   └── style.css             # Full Responsive Styling System (Depth/3D pure CSS)
│   ├── js/
│   │   └── script.js             # Client webcam capture, cart, UPI QR & assistant
│   └── img/products/             # Product Icons & Vector SVGs
│
├── backend/                      # Separated Business Logic Tier (Python / Vercel Serverless)
│   ├── app.py                    # Flask App Factory & Route Blueprint Registry
│   ├── config.py                 # Unified Configuration (Local & Vercel)
│   ├── routes/                   # Modular REST & Controller Blueprints
│   │   ├── auth.py               # Authentication & User Sessions
│   │   ├── inventory.py          # Dashboard, Products CRUD, Alerts & Restock
│   │   ├── billing.py            # POS Cart, Checkout, Bills & Barcodes
│   │   ├── scan.py               # Shelf Vision Scanner & Stock Sync
│   │   ├── reports.py            # Reports & CSV Export
│   │   └── assistant.py          # Offline NLP Smart Assistant Endpoint
│   ├── models/                   # Clean Data Layer Models
│   │   ├── user.py               # User queries & password verification
│   │   ├── product.py            # Inventory queries, metrics & filters
│   │   ├── bill.py               # Transactions & Line Item accounting
│   │   └── scan.py               # Shelf scans & AI crop references
│   ├── services/                 # Deep Modules & Domain Adapters (Codebase Design)
│   │   ├── db.py                 # Supabase (PostgreSQL) + SQLite Adapter Seam
│   │   ├── detection.py          # YOLOv8 + OpenCV Computer Vision Engine
│   │   ├── barcode.py            # EAN-13 Validation & SVG Generator
│   │   └── assistant.py          # Rule-based NLP Query Parser
│   ├── api/
│   │   └── index.py              # Vercel Serverless Function Handler
│   ├── seed_data/
│   │   ├── foods.py              # 133-item Grocery Food Catalog
│   │   └── gen_schema.py         # Schema & seed generator
│   ├── requirements.txt          # Production Python dependencies
│   ├── vercel.json               # Backend Vercel deployment spec
│   └── .env.example              # Backend environment template
│
├── database/                     # Database Artifacts & Migrations
│   ├── invento.db                # Local fallback SQLite database
│   └── supabase_schema.sql       # 1-Click Supabase PostgreSQL Schema & Seeds
│
├── uploads/                      # Uploaded shelf scans & learned crops
│   ├── products/
│   ├── learned/
│   └── crops/
│
├── .env.example                  # Environment template for Supabase & secrets
├── vercel.json                   # Full-stack root deployment routing
├── requirements.txt              # Root Python dependencies
└── README.md
```

---

## ⚡ Connecting Supabase Database

When you are ready with your Supabase project link:

### 1. Initialize Tables in Supabase
1. Open your **[Supabase Dashboard](https://supabase.com/dashboard)**.
2. Select your project and navigate to **SQL Editor** (in the left sidebar).
3. Open `database/supabase_schema.sql` (or `backend/supabase_schema.sql`).
4. Paste the entire content into the SQL Editor and click **Run**.
   - This creates all tables: `users`, `products`, `scans`, `bills`, `bill_items`, `meta`, `product_refs`.
   - Seeds the default admin account: `admin@invento.ai` / `admin123`.
   - Seeds the 133 grocery items with EAN-13 barcodes, categories, and GST rates.

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Add your Supabase project credentials:
```ini
# Supabase REST API credentials
SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_KEY=<your-anon-or-service-role-key>

# OR Direct Supabase PostgreSQL Connection String
# (Supabase -> Settings -> Database -> Connection string -> URI)
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
```

> **Note**: If `SUPABASE_URL` or `DATABASE_URL` is not yet set, the backend **automatically runs on local SQLite** (`database/invento.db`), so you can run and test immediately without any downtime!

---

## 🚀 Running Locally

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Application
Run the backend server:
```bash
python backend/app.py
```
*(Or run `python app.py` from root)*

Open your browser at:
- **Landing Page**: [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
- **Dashboard**: [http://127.0.0.1:5000/dashboard](http://127.0.0.1:5000/dashboard)
- **Login**: Email: `admin@invento.ai` | Password: `admin123`

---

## ☁️ Deploying to Vercel

The repository contains `vercel.json` and `backend/api/index.py` pre-configured for Vercel deployment:

1. Push your repository to GitHub / GitLab.
2. Import the repository in [Vercel](https://vercel.com).
3. In Project Settings -> **Environment Variables**, add:
   - `INVENTO_SECRET_KEY`: Random 32+ character string
   - `DATABASE_URL` (or `SUPABASE_URL` and `SUPABASE_KEY`): Your Supabase credentials
   - `INVENTO_UPI_ID`: Your merchant UPI ID (e.g. `yourname@upi`)
   - `INVENTO_STORE_NAME`: Your store name
4. Click **Deploy**! Vercel will host the frontend assets on its Global Edge Network and execute backend routes via Python Serverless functions.

---

## 🎯 Key Capabilities

- **Deep Module Architecture**: Clean seams between route controllers, data models, and services (`detection`, `barcode`, `assistant`, `db`).
- **Computer Vision Shelf Scanner**: YOLOv8 + OpenCV feature matching with automatic shelf count synchronization.
- **Unified POS Terminal**: Barcode scanner lookup, dynamic cart management, tax calculations, and instant UPI QR payments.
- **Expiry Watchlist**: 7-day proactive expiry tracking, out-of-stock emergency alerts, and 1-click replenishment.
- **Offline NLP Assistant**: Conversational assistant answering inventory, sales, and billing queries.
