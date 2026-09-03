"""
ASU HostelCare Root Application Entry Point & Render/Heroku Compatibility Module
Allows deployment runners calling `app:app`, `main:app`, or `python app.py` to work flawlessly.
"""
import os
import uvicorn
from backend.main import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting ASU HostelCare on port {port}...")
    uvicorn.run("backend.main:app", host=host, port=port, reload=False)
