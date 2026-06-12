from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eeg_tools import bootstrap


class BootstrapTests(unittest.TestCase):
    def test_resolve_repo_root_points_to_project_root(self) -> None:
        repo_root = bootstrap.resolve_repo_root()
        self.assertTrue((repo_root / "infra/compose/docker-compose.dev.yml").exists())

    def test_tool_root_resolves_existing_source_directories(self) -> None:
        bridge_root = bootstrap.tool_root("bridge-runtime")
        replay_root = bootstrap.tool_root("replay-runtime")
        self.assertTrue((bridge_root / "app/main.py").exists())
        self.assertTrue((replay_root / "app/main.py").exists())

    def test_activated_tool_app_sets_runtime_root_env(self) -> None:
        previous = os.environ.get("MCS_EEG_TOOLS_ROOT")
        try:
            with bootstrap.activated_tool_app("bridge-runtime"):
                self.assertEqual(
                    Path(os.environ["MCS_EEG_TOOLS_ROOT"]).resolve(),
                    bootstrap.resolve_repo_root(),
                )
        finally:
            if previous is None:
                os.environ.pop("MCS_EEG_TOOLS_ROOT", None)
            else:
                os.environ["MCS_EEG_TOOLS_ROOT"] = previous


if __name__ == "__main__":
    unittest.main()
