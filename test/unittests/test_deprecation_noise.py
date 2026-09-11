# Copyright 2024, OpenVoiceOS
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Wiring ovos_plugin_manager together must not fire its own deprecation
notices, while an external caller importing a deprecated module still gets
warned exactly once.

Each case runs in a fresh interpreter: module top-level code runs once per
process and ovos_utils deduplicates repeat notices, so counting in-process
would hide the very records under test. Notices reach stdout through the
ovos_utils logger, so the count comes from there.
"""

import subprocess
import sys
import unittest


def _deprecation_count(importer: str) -> int:
    proc = subprocess.run([sys.executable, "-c", importer],
                          capture_output=True, text=True)
    assert proc.returncode == 0, f"import failed:\n{proc.stderr}"
    return proc.stdout.count("Deprecation version=")


class TestDeprecationNoise(unittest.TestCase):
    def test_package_import_is_silent(self):
        self.assertEqual(_deprecation_count("import ovos_plugin_manager"), 0)

    def test_public_reexport_is_silent(self):
        self.assertEqual(
            _deprecation_count("from ovos_plugin_manager import OpenVoiceOSPlugin"),
            0)

    def test_solvers_import_is_silent(self):
        self.assertEqual(
            _deprecation_count("import ovos_plugin_manager.solvers"), 0)

    def test_direct_deprecated_module_still_warns_once(self):
        self.assertEqual(
            _deprecation_count("import ovos_plugin_manager.installation"), 1)

    def test_direct_deprecated_template_still_warns_once(self):
        self.assertEqual(
            _deprecation_count("import ovos_plugin_manager.templates.solvers"),
            1)


if __name__ == "__main__":
    unittest.main()
