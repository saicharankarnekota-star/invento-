"""Vercel Python Serverless entrypoint."""
import sys
import os

# Add parent directory to path so imports work smoothly in Vercel Serverless environment
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../.."))

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from backend.app import app
except ImportError:
    from app import app

# For Vercel Serverless function execution
app = app
