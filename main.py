import os
import uvicorn
from backend.main import app

if __name__ == "__main__":
    # Render, Railway, Heroku pass the port as an environment variable $PORT
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"=======================================================")
    print(f"  ASU HostelCare Server Starting Live on port {port}")
    print(f"  Access locally: http://127.0.0.1:{port}")
    print(f"=======================================================")
    uvicorn.run("backend.main:app", host=host, port=port, reload=False)
