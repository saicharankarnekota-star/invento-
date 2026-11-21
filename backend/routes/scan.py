"""Shelf image upload, AI computer vision scanning, and inventory synchronization."""
import os
import json
import base64
import re
import shutil
from datetime import datetime
from PIL import Image, ImageOps
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory
import backend.config as config
from backend.models.product import ProductModel
from backend.models.scan import ScanModel
from backend.services.db import get_db
from backend.services.detection import ProductDetector
from backend.services.barcode import normalize as ean_normalize
from backend.routes.utils import login_required, allowed_file, to_int

scan_bp = Blueprint("scan", __name__)
detector = ProductDetector()

def reference_image_path(image):
    if not image:
        return None
    if image.startswith("img/"):
        path = os.path.join(config.FRONTEND_DIR, image)
        if path.endswith(".svg"):
            path = path[:-4] + ".png"
    else:
        path = os.path.join(config.PRODUCT_IMG_DIR, os.path.basename(image))
    return path if os.path.exists(path) else None

def get_product_catalog(conn=None):
    close_conn = False
    if conn is None:
        conn = get_db()
        close_conn = True
    learned = {}
    for r in conn.execute("SELECT product_id, filename FROM product_refs ORDER BY id DESC").fetchall():
        path = os.path.join(config.REF_DIR, r["filename"])
        if os.path.exists(path) and len(learned.setdefault(r["product_id"], [])) < 8:
            learned[r["product_id"]].append(path)
    
    rows = conn.execute("SELECT id, name, category, image, barcode FROM products ORDER BY name").fetchall()
    if close_conn:
        conn.close()

    out = []
    for r in rows:
        main = reference_image_path(r["image"])
        out.append({
            "id": r["id"],
            "name": r["name"],
            "category": r["category"],
            "barcode": ean_normalize(r["barcode"]) or (r["barcode"] or ""),
            "reference_path": main,
            "reference_paths": ([main] if main else []) + learned.get(r["id"], [])
        })
    return out

def normalize_upload(path):
    try:
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((1280, 1280))
            im.save(path, "JPEG", quality=88)
        return True
    except Exception:
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
        return False

def learn_from_crops(product_id, files):
    conn = get_db()
    for f in files or []:
        f = os.path.basename(str(f))
        src = os.path.join(config.CROP_DIR, f)
        if re.fullmatch(r"crop_[0-9_]+\.jpg", f) and os.path.exists(src):
            dst_name = f"p{product_id}_{f}"
            shutil.copyfile(src, os.path.join(config.REF_DIR, dst_name))
            conn.execute("INSERT INTO product_refs (product_id, filename) VALUES (?, ?)", (product_id, dst_name))
    conn.commit()
    conn.close()

@scan_bp.route("/static/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(config.UPLOAD_FOLDER, filename)

@scan_bp.route("/scan", methods=["GET", "POST"])
@login_required
def scan():
    scan_result = None

    if request.method == "POST":
        config.ensure_directories()
        file = request.files.get("image")
        webcam_data = request.form.get("webcam_image")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        input_filename = f"scan_{timestamp}.jpg"
        input_path = os.path.join(config.UPLOAD_FOLDER, input_filename)

        image_ready = False
        if file and allowed_file(file.filename):
            file.save(input_path)
            image_ready = True
        elif webcam_data and webcam_data.startswith("data:image"):
            try:
                header, encoded = webcam_data.split(",", 1)
                with open(input_path, "wb") as fh:
                    fh.write(base64.b64decode(encoded))
                image_ready = True
            except Exception:
                image_ready = False

        if image_ready and not normalize_upload(input_path):
            image_ready = False
            flash("That file is not a valid image. Upload a PNG, JPG or WEBP photo.", "danger")

        if image_ready:
            catalog = get_product_catalog()
            result = detector.detect(input_path, output_dir=config.UPLOAD_FOLDER, catalog=catalog)

            if result.get("success"):
                matched, unmatched = result["matched"], result["unmatched"]
                detected_counts = {name: v["count"] for name, v in matched.items()}
                for label, v in unmatched.items():
                    detected_counts[f"{label} (unmatched)"] = v["count"]
                total_count = result["total_count"]

                scan_id, now_str = ScanModel.create(input_filename, result["annotated_filename"], detected_counts, total_count)

                scan_result = {
                    "scan_id": scan_id,
                    "original_image": input_filename,
                    "annotated_image": result["annotated_filename"],
                    "matched": matched,
                    "unmatched": unmatched,
                    "total_count": total_count,
                    "matched_total": result["matched_total"],
                    "sync_counts": {n: v["count"] for n, v in matched.items()},
                    "unmatched_counts": {l: v["count"] for l, v in unmatched.items()},
                    "unmatched_crops": {l: v.get("crops", []) for l, v in unmatched.items()},
                    "model_used": result.get("model_used"),
                    "note": result.get("note"),
                    "timestamp": now_str,
                    "products": [{"id": p["id"], "name": p["name"]} for p in catalog],
                }
                if total_count == 0:
                    flash("The scan finished but no objects were found. Try a closer, brighter photo of the shelf.", "warning")
                else:
                    flash(f"Scan complete: {result['matched_total']} of {total_count} objects matched to your products.", "success")
            else:
                flash(f"Scan could not run: {result.get('error')}", "danger")
        elif not (file or webcam_data):
            flash("Please upload an image or capture a webcam photo to scan.", "warning")

    return render_template("scan.html", scan_result=scan_result)

@scan_bp.route("/scan/sync", methods=["POST"])
@login_required
def sync_scan():
    sync_mode = request.form.get("sync_mode", "update")
    try:
        matched = json.loads(request.form.get("detected_counts") or "{}")
        unmatched = json.loads(request.form.get("unmatched_counts") or "{}")
        crops = json.loads(request.form.get("unmatched_crops") or "{}")
    except Exception:
        flash("Invalid detection data format.", "danger")
        return redirect(url_for("scan.scan"))

    if not matched and not unmatched:
        flash("No detection data provided to sync.", "warning")
        return redirect(url_for("scan.scan"))

    counts, skipped = {}, []
    conn = get_db()
    for name, count in matched.items():
        row = conn.execute("SELECT id FROM products WHERE LOWER(name) = LOWER(?)", (name,)).fetchone()
        if row:
            counts[row["id"]] = counts.get(row["id"], 0) + to_int(count)
        else:
            skipped.append(name)

    for key, value in request.form.items():
        if key.startswith("assign::") and value.isdigit():
            label = key[len("assign::"):]
            val_id = int(value)
            if conn.execute("SELECT 1 FROM products WHERE id = ?", (val_id,)).fetchone():
                counts[val_id] = counts.get(val_id, 0) + to_int(unmatched.get(label, 0))
                learn_from_crops(val_id, crops.get(label, []))
    conn.close()

    updated = ScanModel.sync_counts(counts, sync_mode=sync_mode)
    if updated:
        flash(f"Inventory synchronized successfully! Updated {len(updated)} products: {', '.join(updated)}", "success")
    else:
        flash("Nothing was changed. Assign the unmatched objects to products first, or add product images so they can be recognised.", "warning")
    if skipped:
        flash(f"Skipped unknown products (not in your catalog): {', '.join(skipped)}", "warning")

    return redirect(url_for("inventory.products"))
