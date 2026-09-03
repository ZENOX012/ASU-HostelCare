"""
ASU HostelCare Root Application Entry Point & Render/Heroku Compatibility Module
Allows deployment runners calling `app:app`, `main:app`, or `python app.py` to work flawlessly.
"""
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import uvicorn
from backend.main import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
