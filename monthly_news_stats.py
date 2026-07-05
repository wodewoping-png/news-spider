from __future__ import annotations

import sys

from src.summary import main


if __name__ == "__main__":
    raise SystemExit(main(["monthly", *sys.argv[1:]]))
