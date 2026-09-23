from __future__ import annotations

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from scripts.prepare_dataset import *

if __name__ == "__main__":
    import scripts.prepare_dataset as pd_script
    if hasattr(pd_script, "main"):
        pd_script.main()