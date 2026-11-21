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
        identifier = (request.form.get("email") or request.form.get("username") or "").strip().lower()
        password = request.form.get("password", "").strip()

        authenticated = False
        supabase_token = None
        supabase_user_id = None

        # Resolve email if username was provided
        target_email = identifier
        if "@" not in target_email:
            user_db = UserModel.get_by_identifier(identifier)
            if user_db:
                try:
                    target_email = user_db["email"] or f"{identifier}@invento.ai"
                except Exception:
                    target_email = f"{identifier}@invento.ai"
            else:
                target_email = f"{identifier}@invento.ai"

        # 1. Attempt Supabase Auth login
        auth_resp = sign_in_supabase(target_email, password)
        if auth_resp and getattr(auth_resp, "user", None):
            authenticated = True
            supabase_user_id = auth_resp.user.id
            if getattr(auth_resp, "session", None) and getattr(auth_resp.session, "access_token", None):
                supabase_token = auth_resp.session.access_token

        # 2. Match with local/database persona
        user = UserModel.get_by_identifier(target_email) or UserModel.get_by_identifier(identifier)

        # 3. Fallback verification if Supabase Auth network call was not used or failed
        if not authenticated and user:
            if UserModel.verify_password(user["password"], password):
                authenticated = True

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

    return render_template("login.html")

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
                sign_up_supabase(email, password, metadata={"name": name, "role": role})
                # 2. Create in application database
                UserModel.create(name=name, email=email, password=password, role=role)

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
