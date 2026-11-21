"""Root Vercel Serverless entrypoint."""
import sys
import os
import types

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

if "backend" not in sys.modules and os.path.exists(BACKEND_DIR):
    backend_pkg = types.ModuleType("backend")
    backend_pkg.__path__ = [BACKEND_DIR]
    backend_pkg.__file__ = os.path.join(BACKEND_DIR, "__init__.py")
    sys.modules["backend"] = backend_pkg

try:
    from backend.app import app
except ImportError:
    from app import app

# Vercel WSGI entrypoint
app = app

