"""INVENTO AI Supabase Storage Service.
Handles object storage for product images and shelf scan captures
using Supabase Storage with graceful local filesystem fallback.
"""
import os
import io
import secrets
from PIL import Image
import backend.config as config
from backend.services.supabase_client import get_supabase_client

def upload_file_bytes(bucket_name: str, file_bytes: bytes, filename: str, content_type: str = "image/jpeg") -> str:
    """Uploads bytes to a Supabase bucket and returns its public URL, or None if failed."""
    client = get_supabase_client()
    if client:
        try:
            client.storage.from_(bucket_name).upload(
                path=filename,
                file=file_bytes,
                file_options={"content-type": content_type, "upsert": "true"}
            )
            public_url = client.storage.from_(bucket_name).get_public_url(filename)
            print(f"[Supabase Storage] Uploaded {filename} to {bucket_name}: {public_url}")
            return public_url
        except Exception as e:
            print(f"[Supabase Storage] Upload failed for {filename}: {e}")
    return None

def save_product_image_to_supabase_or_local(file) -> str:
    """Validates, optimizes and stores a product image.
    Uploads directly to Supabase Storage 'invento-products' bucket and
    caches locally. Returns public URL or filename.
    """
    if not file or not getattr(file, "filename", None):
        return None

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in config.ALLOWED_EXTENSIONS:
        return None

    try:
        img = Image.open(file.stream)
        img.load()
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            bg = Image.new("RGB", img.size, "white")
            bg.paste(img, mask=img.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")
        
        img.thumbnail((640, 640))
        filename = f"product_{secrets.token_hex(8)}.jpg"

        # Buffer for Supabase upload
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=86)
        file_bytes = buf.getvalue()

        # Cache locally
        config.ensure_directories()
        local_path = os.path.join(config.PRODUCT_IMG_DIR, filename)
        with open(local_path, "wb") as f:
            f.write(file_bytes)

        # Upload to Supabase Storage
        public_url = upload_file_bytes("invento-products", file_bytes, filename, "image/jpeg")
        if public_url:
            return public_url

        return filename
    except Exception as e:
        print(f"[Storage Error] Failed to process product image: {e}")
        return None

def save_scan_image_to_supabase_or_local(pil_image_or_bytes, filename: str, is_annotated: bool = False) -> str:
    """Saves a shelf scan image to Supabase 'invento-scans' bucket and local disk."""
    config.ensure_directories()
    
    if isinstance(pil_image_or_bytes, Image.Image):
        buf = io.BytesIO()
        pil_image_or_bytes.save(buf, format="JPEG", quality=88)
        file_bytes = buf.getvalue()
    elif isinstance(pil_image_or_bytes, bytes):
        file_bytes = pil_image_or_bytes
    else:
        return None

    # Save local copy
    local_path = os.path.join(config.UPLOAD_FOLDER, filename)
    try:
        with open(local_path, "wb") as f:
            f.write(file_bytes)
    except Exception:
        pass

    # Upload to Supabase Storage
    public_url = upload_file_bytes("invento-scans", file_bytes, filename, "image/jpeg")
    return public_url or filename
