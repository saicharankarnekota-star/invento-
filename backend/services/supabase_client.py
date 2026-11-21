"""INVENTO AI Supabase Client & SDK Helper.
Provides unified access to Supabase Auth, Storage, and Database.
"""
import backend.config as config

_client = None

def get_supabase_client():
    """Retrieve singleton Supabase client instance."""
    global _client
    if _client is not None:
        return _client
    
    url = config.SUPABASE_URL
    key = config.SUPABASE_KEY
    if url and key:
        try:
            from supabase import create_client
            _client = create_client(url, key)
            return _client
        except Exception as e:
            print(f"[Supabase] Could not initialize Supabase client: {e}")
    return None

def sign_in_supabase(email: str, password: str):
    """Authenticate credentials against Supabase Auth.
    Returns (user, session) on success, or None on failure.
    """
    client = get_supabase_client()
    if not client:
        return None
    try:
        resp = client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        return resp
    except Exception as e:
        print(f"[Supabase Auth] sign_in_with_password notice: {e}")
        return None

def sign_up_supabase(email: str, password: str, metadata: dict = None):
    """Register a new user with Supabase Auth."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        options = {"data": metadata} if metadata else {}
        resp = client.auth.sign_up({
            "email": email,
            "password": password,
            "options": options
        })
        return resp
    except Exception as e:
        print(f"[Supabase Auth] sign_up notice: {e}")
        return None

def sign_out_supabase():
    """Sign out from Supabase Auth."""
    client = get_supabase_client()
    if not client:
        return
    try:
        client.auth.sign_out()
    except Exception as e:
        print(f"[Supabase Auth] sign_out notice: {e}")
