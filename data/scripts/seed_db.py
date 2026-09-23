from __future__ import annotations

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from scripts.seed_db import seed, _seed_local_memory_fallback

if __name__ == "__main__":
    seed()
