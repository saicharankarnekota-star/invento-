"""User model and authentication queries."""
import re
from werkzeug.security import generate_password_hash, check_password_hash
from backend.services.db import get_db

class UserModel:
    @staticmethod
    def get_by_id(user_id):
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        return user

    @staticmethod
    def get_by_identifier(identifier):
        if not identifier:
            return None
        clean_id = identifier.strip().lower()
        no_spaces = clean_id.replace(" ", "")
        conn = get_db()
        sql = """
            SELECT * FROM users 
            WHERE lower(email) = ? 
               OR lower(username) = ? 
               OR lower(name) = ?
               OR lower(replace(name, ' ', '')) = ?
            ORDER BY id ASC LIMIT 1
        """
        user = conn.execute(sql, (clean_id, clean_id, clean_id, no_spaces)).fetchone()
        conn.close()
        return user

    @staticmethod
    def verify_password(stored_hash, candidate_password):
        if not stored_hash or candidate_password is None:
            return False
        if stored_hash.startswith(("scrypt:", "pbkdf2:")):
            if check_password_hash(stored_hash, candidate_password):
                return True
            if candidate_password.strip() != candidate_password:
                if check_password_hash(stored_hash, candidate_password.strip()):
                    return True
            return False
        # Legacy plain text migration check
        return stored_hash == candidate_password or stored_hash == candidate_password.strip()

    @staticmethod
    def update_password(user_id, raw_password):
        conn = get_db()
        conn.execute("UPDATE users SET password = ? WHERE id = ?", (generate_password_hash(raw_password.strip(), method='pbkdf2:sha256'), user_id))
        conn.commit()
        conn.close()

    @staticmethod
    def create(name, email, password, role="staff"):
        conn = get_db()
        clean_email = (email or "").strip().lower()
        clean_pwd = (password or "").strip()
        clean_name = (name or "").strip()
        base_username = clean_email.split("@")[0] if "@" in clean_email else clean_email
        pwd_hash = generate_password_hash(clean_pwd, method='pbkdf2:sha256') if clean_pwd else 'supabase_auth'

        # Check if user with this email or username already exists; if so, update safely
        existing = conn.execute("SELECT id FROM users WHERE lower(email) = ? OR lower(username) = ?",
                                (clean_email, base_username)).fetchone()
        if existing:
            user_id = existing["id"] if isinstance(existing, dict) or hasattr(existing, '__getitem__') else existing[0]
            conn.execute("UPDATE users SET password = ?, role = ?, email = ?, name = ? WHERE id = ?",
                         (pwd_hash, role, clean_email, clean_name, user_id))
            conn.commit()
            conn.close()
            return user_id

        # Insert new record
        cur = conn.execute("""
            INSERT INTO users (username, password, role, email, name)
            VALUES (?, ?, ?, ?, ?)
        """, (base_username, pwd_hash, role, clean_email, clean_name))
        new_id = cur.lastrowid if hasattr(cur, 'lastrowid') else None
        conn.commit()
        conn.close()
        return new_id

    @staticmethod
    def get_all():
        conn = get_db()
        users = conn.execute("SELECT id, username, email, name, role FROM users ORDER BY role, name").fetchall()
        conn.close()
        return users
