"""Prefer container dependencies; fall back to read-only JetPack Python packages."""
import os
import sys

for directory in (
    "/opt/jetson/python",
    "/opt/jetson/user-python",
    "/opt/jetson/system-python",
):
    if os.path.isdir(directory) and directory not in sys.path:
        sys.path.append(directory)
