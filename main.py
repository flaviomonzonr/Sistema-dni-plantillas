"""
Root entrypoint for Render, cloud platforms, and local execution.
Enables running:
  - uvicorn main:app --host 0.0.0.0 --port $PORT
  - uvicorn backend.main:app --host 0.0.0.0 --port $PORT
  - gunicorn -k uvicorn.workers.UvicornWorker main:app
"""
import sys
import os
from pathlib import Path

# Ensure root directory and backend directory are always at the front of sys.path
_ROOT = Path(__file__).resolve().parent
_BACKEND = _ROOT / "backend"

for _p in [str(_ROOT), str(_BACKEND)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend.main import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
