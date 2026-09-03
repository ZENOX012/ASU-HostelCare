import sys
import os

# Ensure project root is always in sys.path regardless of runner directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import uvicorn
from backend.main import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"=======================================================")
    print(f"  ASU HostelCare Server Starting Live on {host}:{port}")
    print(f"=======================================================")
    uvicorn.run(app, host=host, port=port)
