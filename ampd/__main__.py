"""`python -m ampd` → start the API server."""
import uvicorn

from .config import config

if __name__ == "__main__":
    uvicorn.run("ampd.main:app", host=config.host, port=config.port, log_level="info")
