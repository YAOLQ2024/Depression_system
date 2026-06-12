from __future__ import annotations

# This module exists to make dynamic bridge/replay dependencies visible to
# freezer tooling such as PyInstaller.
import argparse  # noqa: F401
import asyncio  # noqa: F401
import base64  # noqa: F401
import dataclasses  # noqa: F401
import datetime  # noqa: F401
import functools  # noqa: F401
import json  # noqa: F401
import logging  # noqa: F401
import math  # noqa: F401
import os  # noqa: F401
import pathlib  # noqa: F401
import queue  # noqa: F401
import threading  # noqa: F401
import time  # noqa: F401
import uuid  # noqa: F401

try:  # pragma: no cover - build/runtime dependency exposure only
    import bleak  # noqa: F401
except Exception:
    pass

try:  # pragma: no cover - build/runtime dependency exposure only
    import redis  # noqa: F401
except Exception:
    pass
