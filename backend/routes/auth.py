"""Authentication and session management routes with Supabase Auth integration."""
import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from backend.models.user import UserModel
from backend.services.supabase_client import sign_in_supabase, sign_up_supabase, sign_out_supabase

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/")
def index():
    if "user" in session:
        return redirect(url_for("inventory.dashboard"))
    return redirect(url_for("auth.login"))

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("inventory.dashboard"))

    if request.method == "POST":
        raw_identifier = request.form.get("email") or request.form.get("username") or ""
        identifier = raw_identifier.strip()
        identifier_lower = identifier.lower()
        password = request.form.get("password", "")

        authenticated = False
        supabase_token = None
        supabase_user_id = None

        # 1. Match with database persona first (email, username, or name)
        user = UserModel.get_by_identifier(identifier_lower)

        target_email = ""
        if user and user["email"]:
            target_email = user["email"]
        elif "@" in identifier_lower:
            target_email = identifier_lower
        else:
            target_email = f"{identifier_lower}@invento.ai"

        # 2. Database password verification
        if user and UserModel.verify_password(user["password"], password):
            authenticated = True

        # 3. Supabase Auth verification
        auth_resp = sign_in_supabase(target_email, password)
        if auth_resp and getattr(auth_resp, "user", None):
            authenticated = True
            supabase_user_id = auth_resp.user.id
            if getattr(auth_resp, "session", None) and getattr(auth_resp.session, "access_token", None):
                supabase_token = auth_resp.session.access_token

            # Auto-provision user in DB if registered via Supabase Auth
            if not user:
                user_meta = getattr(auth_resp.user, "user_metadata", {}) or {}
                user_name = user_meta.get("name") or identifier.split("@")[0]
                user_role = user_meta.get("role") or "customer"
                user_id = UserModel.create(name=user_name, email=target_email, password=password, role=user_role)
                user = UserModel.get_by_id(user_id)
            elif user and str(user["password"]).startswith("supabase_auth"):
                UserModel.update_password(user["id"], password)
                user = UserModel.get_by_id(user["id"])

        if authenticated and user:
            session.permanent = True
            session["user"] = user["name"] or user["username"]
            session["email"] = user["email"] or target_email
            session["role"] = user["role"]
            if supabase_token:
                session["supabase_token"] = supabase_token
            if supabase_user_id:
                session["supabase_user_id"] = supabase_user_id

            flash(f"Welcome back, {session['user']}!", "success")
            return redirect(url_for("inventory.dashboard"))

        flash("Invalid email or password. Please try again.", "danger")
        return render_template("login.html", form_email=raw_identifier)

    return render_template("login.html", form_email="")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if "user" in session:
        return redirect(url_for("inventory.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()[:60]
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        error = None
        if not name:
            error = "Enter your full name."
        elif not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            error = "Enter a valid email address."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != confirm:
            error = "Passwords do not match."

        role = (request.form.get("role") or "").strip().lower()
        if role not in ("customer", "cashier", "inventory_manager", "admin"):
            role = "customer"

        if not error:
            existing = UserModel.get_by_identifier(email)
            if existing:
                error = "An account with this email already exists. Sign in instead."
            else:
                # 1. Register with Supabase Auth
                auth_resp = sign_up_supabase(email, password, metadata={"name": name, "role": role})

                # 2. Auto-confirm in auth.users if connected to Supabase PostgreSQL
                try:
                    from backend.services.db import get_db
                    conn = get_db()
                    if conn.is_postgres:
                        conn.execute("UPDATE auth.users SET email_confirmed_at = NOW() WHERE lower(email) = ? AND email_confirmed_at IS NULL", (email,))
                        conn.commit()
                    conn.close()
                except Exception as e:
                    print(f"[Supabase Auth Notice] auto-confirm notice: {e}")

                # 3. Create in application database
                new_id = UserModel.create(name=name, email=email, password=password, role=role)

                # 4. Instant session creation so user is logged in immediately
                session.permanent = True
                session["user"] = name
                session["email"] = email
                session["role"] = role
                if auth_resp and getattr(auth_resp, "session", None) and getattr(auth_resp.session, "access_token", None):
                    session["supabase_token"] = auth_resp.session.access_token
                if auth_resp and getattr(auth_resp, "user", None):
                    session["supabase_user_id"] = auth_resp.user.id

                flash(f"Account created successfully! Welcome, {name}!", "success")
                return redirect(url_for("inventory.dashboard"))

        if error:
            flash(error, "danger")
            return render_template("register.html", form_name=name, form_email=email)

        flash("Account created. Sign in with your email and password.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html", form_name="", form_email="")

@auth_bp.route("/logout")
def logout():
    sign_out_supabase()
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("auth.login"))
