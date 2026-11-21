import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))

# Robust multi-layout frontend folder detection
if os.path.exists(os.path.join(ROOT_DIR, "frontend", "dashboard.html")):
    FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
elif os.path.exists(os.path.join(BASE_DIR, "frontend", "dashboard.html")):
    FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
elif os.path.exists(os.path.join(ROOT_DIR, "templates", "dashboard.html")):
    FRONTEND_DIR = os.path.join(ROOT_DIR, "templates")
else:
    FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Automatically load .env file if present
def _load_env():
    for env_file in [os.path.join(ROOT_DIR, ".env"), os.path.join(BASE_DIR, ".env")]:
        if os.path.exists(env_file):
            try:
                with open(env_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip("\"'")
                            os.environ.setdefault(k, v)
            except Exception:
                pass
_load_env()

ON_VERCEL = bool(os.environ.get("VERCEL"))

# Secret Key
SECRET_KEY = os.environ.get("INVENTO_SECRET_KEY") or secrets.token_hex(32)

# Database Configuration: Supabase & SQLite fallback
SUPABASE_URL = (os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or "").strip()
SUPABASE_KEY = (os.environ.get("SUPABASE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY") or "").strip()
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

# Local / Serverless SQLite DB fallback
DEFAULT_SQLITE_PATH = "/tmp/invento.db" if ON_VERCEL else os.path.join(ROOT_DIR, "database", "invento.db")
DB_PATH = os.environ.get("INVENTO_DB") or DEFAULT_SQLITE_PATH

# Uploads Folder
DEFAULT_UPLOAD_DIR = "/tmp/uploads" if ON_VERCEL else os.path.join(ROOT_DIR, "uploads")
UPLOAD_FOLDER = os.environ.get("INVENTO_UPLOADS") or DEFAULT_UPLOAD_DIR
PRODUCT_IMG_DIR = os.path.join(UPLOAD_FOLDER, "products")
REF_DIR = os.path.join(UPLOAD_FOLDER, "learned")
CROP_DIR = os.path.join(UPLOAD_FOLDER, "crops")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max

# Payment Settings
MERCHANT_UPI_ID = os.environ.get("INVENTO_UPI_ID", "invento.store@upi")
MERCHANT_NAME = os.environ.get("INVENTO_STORE_NAME", "INVENTO AI Store")

# Billing Settings
DELIVERY_FEE = 25.0
FREE_DELIVERY_ABOVE = 199.0
GST_DEFAULTS = {
    "Beverages": 12,
    "Dairy": 0,
    "Snacks": 12,
    "Personal Care": 18,
    "Produce": 0,
    "Bakery": 18,
    "Staples": 5,
    "Instant Food": 12,
    "Spices & Sauces": 12,
    "Sweets & Chocolates": 18,
    "Dry Fruits": 12
}

SEED_IMAGES = {
    "Coca Cola": "coca-cola.svg",
    "Pepsi": "pepsi.svg",
    "Milk": "milk.svg",
    "Biscuits": "biscuits.svg",
    "Soap": "soap.svg",
    "Shampoo": "shampoo.svg",
    "Fresh Apple": "apple.svg",
    "Instant Noodles": "noodles.svg"
}

def ensure_directories():
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(PRODUCT_IMG_DIR, exist_ok=True)
    os.makedirs(REF_DIR, exist_ok=True)
    os.makedirs(CROP_DIR, exist_ok=True)
