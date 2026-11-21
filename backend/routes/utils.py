"""Shared utility functions and decorators for route blueprints."""
import os
import re
import secrets
from functools import wraps
from datetime import datetime, date
from flask import session, redirect, url_for, flash
from PIL import Image
import backend.config as config

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in config.ALLOWED_EXTENSIONS

def to_int(value, default=0, minimum=0):
    try:
        return max(minimum, int(float(value)))
    except (TypeError, ValueError):
        return default

def to_float(value, default=0.0, minimum=0.0):
    try:
        return max(minimum, float(value))
    except (TypeError, ValueError):
        return default

def get_expiry_info(expiry_date_str):
    if not expiry_date_str:
        return {"status": "none", "label": "No Date Set", "days": None, "badge": "badge-light", "date": ""}
    try:
        exp_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
        diff = (exp_date - date.today()).days
        if diff < 0:
            return {"status": "expired", "label": f"Expired ({abs(diff)}d ago)", "days": diff, "badge": "badge-danger", "date": expiry_date_str}
        elif diff <= 7:
            return {"status": "expiring_soon", "label": f"Expires in {diff}d", "days": diff, "badge": "badge-warning", "date": expiry_date_str}
        else:
            return {"status": "good", "label": f"Fresh ({diff}d left)", "days": diff, "badge": "badge-success", "date": expiry_date_str}
    except Exception:
        return {"status": "none", "label": expiry_date_str, "days": None, "badge": "badge-light", "date": expiry_date_str}

from backend.services.storage import save_product_image_to_supabase_or_local

def save_product_image(file):
    """Validate, resize and store an uploaded product image.
    Uploads to Supabase Storage with local cache fallback.
    Returns the file name/URL or None."""
    if not file or not file.filename:
        return None
    if not allowed_file(file.filename):
        flash("Product image must be a JPG, PNG or WEBP file.", "warning")
        return None
    res = save_product_image_to_supabase_or_local(file)
    if not res:
        flash("Could not read that image. Try a different file.", "warning")
    return res

def remove_product_image(filename):
    if filename:
        path = os.path.join(config.PRODUCT_IMG_DIR, os.path.basename(filename))
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
