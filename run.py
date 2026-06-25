from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    # reload=True no Windows costuma deixar dois processos na mesma porta e travar o SQLite.
    reload = os.getenv("APP_RELOAD", "false").lower() == "true"
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=reload)
