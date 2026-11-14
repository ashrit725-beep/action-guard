"""The Vercel Function that answers every /api/... address (vercel.json sends them here).

It is a doorway, not a second app: it puts backend/ on the import path and hands Vercel the same
FastAPI app the container runs (backend/server.py). The website is built from frontend/ and served
by Vercel's CDN, never by this function. Its packages come from api/requirements.txt.
"""
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Tell the app it runs as a Vercel Function, even if the project does not expose Vercel's own
# system variables: no always-running email worker, and setup problems answered instead of fatal.
os.environ.setdefault("VEXEN_PLATFORM", "vercel")

import server  # noqa: E402  backend/server.py

# Vercel looks for an ASGI application named `app` in this file.
app = server.app
