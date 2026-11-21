"""Vercel Python Serverless entrypoint."""
import sys
import os
import types

# Add directories to path so imports work smoothly in all Vercel configurations
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../.."))

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# If deployed with Root Directory = 'backend', alias 'backend' to BACKEND_DIR
if "backend" not in sys.modules:
    backend_pkg = types.ModuleType("backend")
    backend_pkg.__path__ = [BACKEND_DIR]
    backend_pkg.__file__ = os.path.join(BACKEND_DIR, "__init__.py")
    sys.modules["backend"] = backend_pkg

try:
    from backend.app import app
except ImportError:
    from app import app

# For Vercel Serverless function execution
app = app
