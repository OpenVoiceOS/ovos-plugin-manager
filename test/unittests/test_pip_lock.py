"""The pip lock holds across processes and threads, and needs no combo-lock."""
import os
import re
import subprocess
import sys
import threading
import time
import unittest
from importlib.metadata import requires
from pathlib import Path
from tempfile import gettempdir
from unittest.mock import MagicMock, patch

HOLD_SECONDS = 1.5

# File name that combo-lock 0.3.1 NamedLock("ovos_pip.lock") uses.
COMBO_LOCK_PATH = Path(gettempdir(), "combo_locks", "b3Zvc19waXAubG9jaw==.lock")

HOLDER = f"""
import time
from ovos_plugin_manager.installation import PIP_LOCK
with PIP_LOCK:
    print("held", flush=True)
    time.sleep({HOLD_SECONDS})
"""


def requirement_names(dist: str) -> set:
    return {re.split(r"[\s;<>=!~\[]", req, maxsplit=1)[0].lower().replace("_", "-")
            for req in requires(dist) or []}


class TestPipLock(unittest.TestCase):
    def test_metadata_requires_filelock_not_combo_lock(self):
        names = requirement_names("ovos-plugin-manager")
        self.assertNotIn("combo-lock", names)
        self.assertIn("filelock", names)

    def test_lock_file_is_the_combo_lock_path(self):
        from ovos_plugin_manager.installation import PIP_LOCK
        self.assertEqual(Path(PIP_LOCK.lock_file), COMBO_LOCK_PATH)
        with PIP_LOCK:
            self.assertEqual(os.stat(COMBO_LOCK_PATH).st_mode & 0o777, 0o666)

    @patch("ovos_plugin_manager.installation.os.access", return_value=True)
    @patch("ovos_plugin_manager.installation.exists", return_value=False)
    @patch("ovos_plugin_manager.installation.Popen")
    def test_pip_install_waits_for_other_process(self, popen, _exists, _access):
        from ovos_plugin_manager.installation import pip_install
        proc = MagicMock()
        proc.wait.return_value = 0
        popen.return_value = proc
        holder = subprocess.Popen([sys.executable, "-c", HOLDER],
                                  stdout=subprocess.PIPE, text=True)
        try:
            # The package logs to stdout, so skip lines until the marker.
            self.assertIn("held", (line.strip() for line in holder.stdout))
            start = time.monotonic()
            self.assertTrue(pip_install(["some-package"]))
            waited = time.monotonic() - start
        finally:
            holder.wait(timeout=30)
        self.assertEqual(holder.returncode, 0)
        self.assertGreater(waited, HOLD_SECONDS / 2)
        popen.assert_called_once()

    def test_other_thread_waits_for_release(self):
        from ovos_plugin_manager.installation import PIP_LOCK
        held = threading.Event()

        def hold():
            with PIP_LOCK:
                held.set()
                time.sleep(HOLD_SECONDS)

        holder = threading.Thread(target=hold)
        holder.start()
        self.assertTrue(held.wait(timeout=10))
        start = time.monotonic()
        with PIP_LOCK:
            waited = time.monotonic() - start
        holder.join()
        self.assertGreater(waited, HOLD_SECONDS / 2)


if __name__ == "__main__":
    unittest.main()
