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
        identifier = identifier.strip().lower()
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE lower(email) = ? OR lower(username) = ?",
                            (identifier, identifier)).fetchone()
        conn.close()
        return user

    @staticmethod
    def verify_password(stored_hash, candidate_password):
        if not stored_hash or not candidate_password:
            return False
        if stored_hash.startswith(("scrypt:", "pbkdf2:")):
            return check_password_hash(stored_hash, candidate_password)
        # Legacy plain text migration check
        return stored_hash == candidate_password

    @staticmethod
    def update_password(user_id, raw_password):
        conn = get_db()
        conn.execute("UPDATE users SET password = ? WHERE id = ?", (generate_password_hash(raw_password, method='pbkdf2:sha256'), user_id))
        conn.commit()
        conn.close()

    @staticmethod
    def create(name, email, password, role="staff"):
        conn = get_db()
        cur = conn.execute("""
            INSERT INTO users (username, password, role, email, name)
            VALUES (?, ?, ?, ?, ?)
        """, (email, generate_password_hash(password, method='pbkdf2:sha256'), role, email, name))
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
