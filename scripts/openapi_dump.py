"""Dump the app's OpenAPI schema to stdout — the contract-of-record
generator (#128). Run: python3 scripts/openapi_dump.py > api/openapi.json
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tonearm.main import app          # noqa: E402

if __name__ == "__main__":
    json.dump(app.openapi(), sys.stdout, indent=1, sort_keys=True)
    sys.stdout.write("\n")
