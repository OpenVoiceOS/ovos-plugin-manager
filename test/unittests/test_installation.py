import unittest
from unittest.mock import patch, MagicMock, call

from ovos_plugin_manager.exceptions import PipException


class TestPipInstall(unittest.TestCase):

    def _make_proc(self, returncode=0, stdout=b"", stderr=b""):
        proc = MagicMock()
        proc.wait.return_value = returncode
        proc.stdout.read.return_value = stdout
        proc.stderr.read.return_value = stderr
        return proc

    def test_empty_packages_returns_false(self):
        from ovos_plugin_manager.installation import pip_install
        result = pip_install([])
        self.assertFalse(result)

    @patch("ovos_plugin_manager.installation.Popen")
    @patch("ovos_plugin_manager.installation.exists", return_value=False)
    @patch("ovos_plugin_manager.installation.os.access", return_value=True)
    def test_success_returns_true(self, mock_access, mock_exists, mock_popen):
        from ovos_plugin_manager.installation import pip_install
        mock_popen.return_value = self._make_proc(returncode=0)
        result = pip_install(["some-package"])
        self.assertTrue(result)
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        self.assertIn("some-package", cmd)
        self.assertIn("install", cmd)

    @patch("ovos_plugin_manager.installation.Popen")
    @patch("ovos_plugin_manager.installation.exists", return_value=False)
    @patch("ovos_plugin_manager.installation.os.access", return_value=True)
    def test_failure_raises_pip_exception(self, mock_access, mock_exists, mock_popen):
        from ovos_plugin_manager.installation import pip_install
        mock_popen.return_value = self._make_proc(returncode=1,
                                                  stdout=b"",
                                                  stderr=b"error msg")
        with self.assertRaises(PipException):
            pip_install(["bad-package"])

    @patch("ovos_plugin_manager.installation.Popen")
    @patch("ovos_plugin_manager.installation.exists", return_value=False)
    @patch("ovos_plugin_manager.installation.os.access", return_value=True)
    def test_multiple_packages_installed_sequentially(self, mock_access,
                                                       mock_exists, mock_popen):
        from ovos_plugin_manager.installation import pip_install
        mock_popen.return_value = self._make_proc(returncode=0)
        pip_install(["pkg-a", "pkg-b", "pkg-c"])
        self.assertEqual(mock_popen.call_count, 3)

    @patch("ovos_plugin_manager.installation.Popen")
    @patch("ovos_plugin_manager.installation.exists", return_value=False)
    @patch("ovos_plugin_manager.installation.os.access", return_value=False)
    def test_uses_sudo_when_not_writable(self, mock_access, mock_exists,
                                          mock_popen):
        from ovos_plugin_manager.installation import pip_install
        mock_popen.return_value = self._make_proc(returncode=0)
        pip_install(["pkg"])
        cmd = mock_popen.call_args[0][0]
        self.assertIn("sudo", cmd)

    @patch("ovos_plugin_manager.installation.Popen")
    @patch("ovos_plugin_manager.installation.exists", side_effect=lambda p: p == "/etc/mycroft/constraints.txt")
    @patch("ovos_plugin_manager.installation.os.access", return_value=True)
    def test_uses_default_constraints_when_present(self, mock_access,
                                                     mock_exists, mock_popen):
        from ovos_plugin_manager.installation import pip_install
        mock_popen.return_value = self._make_proc(returncode=0)
        pip_install(["pkg"])
        cmd = mock_popen.call_args[0][0]
        self.assertIn("-c", cmd)
        self.assertIn("/etc/mycroft/constraints.txt", cmd)

    @patch("ovos_plugin_manager.installation.Popen")
    @patch("ovos_plugin_manager.installation.exists", return_value=False)
    @patch("ovos_plugin_manager.installation.os.access", return_value=True)
    def test_missing_constraints_file_returns_false(self, mock_access,
                                                     mock_exists, mock_popen):
        from ovos_plugin_manager.installation import pip_install
        # exists() returns False for everything, including the given constraints
        result = pip_install(["pkg"], constraints="/nonexistent/constraints.txt")
        self.assertFalse(result)
        mock_popen.assert_not_called()


class TestPipException(unittest.TestCase):
    def test_is_runtime_error(self):
        exc = PipException("pip failed")
        self.assertIsInstance(exc, RuntimeError)

    def test_message(self):
        exc = PipException("something went wrong")
        self.assertIn("something went wrong", str(exc))
