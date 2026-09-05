import unittest
from unittest.mock import patch, MagicMock, call

from ovos_plugin_manager.exceptions import PipException


class TestPipInstall(unittest.TestCase):

    def _make_proc(self, returncode=0, stdout=b"", stderr=b""):
        """
        Create a MagicMock that simulates a subprocess-like object with configurable exit code and I/O.
        
        Parameters:
            returncode (int): Value returned by proc.wait().
            stdout (bytes): Bytes returned by proc.stdout.read().
            stderr (bytes): Bytes returned by proc.stderr.read().
        
        Returns:
            MagicMock: Mock process with wait(), stdout.read(), and stderr.read() preset to the provided values.
        """
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


class TestPipInstallStringArg(unittest.TestCase):
    """pip_install accepts a plain string as well as a list."""

    @patch("ovos_plugin_manager.installation.Popen")
    @patch("ovos_plugin_manager.installation.exists", return_value=False)
    @patch("ovos_plugin_manager.installation.os.access", return_value=True)
    def test_string_package_accepted(self, mock_access, mock_exists, mock_popen):
        from ovos_plugin_manager.installation import pip_install
        proc = MagicMock()
        proc.wait.return_value = 0
        mock_popen.return_value = proc
        result = pip_install("single-package")
        self.assertTrue(result)
        cmd = mock_popen.call_args[0][0]
        self.assertIn("single-package", cmd)

    @patch("ovos_plugin_manager.installation.Popen")
    @patch("ovos_plugin_manager.installation.exists", return_value=False)
    @patch("ovos_plugin_manager.installation.os.access", return_value=True)
    def test_print_logs_true_no_pipe(self, mock_access, mock_exists, mock_popen):
        from ovos_plugin_manager.installation import pip_install, PIPE
        proc = MagicMock()
        proc.wait.return_value = 0
        mock_popen.return_value = proc
        pip_install(["pkg"], print_logs=True)
        # When print_logs=True, Popen is called WITHOUT stdout/stderr pipes
        _, kwargs = mock_popen.call_args
        self.assertNotIn("stdout", kwargs)
        self.assertNotIn("stderr", kwargs)


class TestSearchPip(unittest.TestCase):

    def _html_response(self, names, descs, query="ovos", page=1,
                       extra_pages=False):
        """Build a minimal HTML blob that matches the parsing logic."""
        names_html = "".join(
            f'<span class="package-snippet__name">{n}</span>' for n in names
        )
        descs_html = "".join(
            f'<p class="package-snippet__description">{d}</p>' for d in descs
        )
        page_html = ""
        if extra_pages:
            page_html = (
                f'<a href="/search/?q={query}&amp;page={page + 1}'
                f'button-group__button">{page + 1}</a>'
            )
        return (
            f'<span class="package-snippet__name">DUMMY</span>'  # split[0] is ignored
            + names_html
            + '<span class="package-snippet__name">DUMMY</span>'  # last split ignored
            + f'<p class="package-snippet__description">DUMMY</p>'
            + descs_html
            + f'<p class="package-snippet__description">DUMMY</p>'
            + page_html
        )

    @patch("ovos_plugin_manager.installation.requests.get")
    def test_yields_name_desc_tuples(self, mock_get):
        from ovos_plugin_manager.installation import search_pip
        mock_get.return_value.text = self._html_response(
            ["ovos-tts-plugin-piper", "ovos-stt-plugin-whisper"],
            ["A piper TTS plugin", "A whisper STT plugin"],
        )
        results = list(search_pip("ovos", strict=False, max_results=10))
        self.assertEqual(len(results), 2)
        names = [r[0] for r in results]
        self.assertIn("ovos-tts-plugin-piper", names)

    @patch("ovos_plugin_manager.installation.requests.get")
    def test_strict_mode_filters_by_query(self, mock_get):
        from ovos_plugin_manager.installation import search_pip
        mock_get.return_value.text = self._html_response(
            ["ovos-plugin", "unrelated-pkg"],
            ["An OVOS plugin", "Unrelated"],
        )
        results = list(search_pip("ovos", strict=True, max_results=10))
        names = [r[0] for r in results]
        self.assertIn("ovos-plugin", names)
        self.assertNotIn("unrelated-pkg", names)

    @patch("ovos_plugin_manager.installation.requests.get")
    def test_respects_max_results(self, mock_get):
        from ovos_plugin_manager.installation import search_pip
        many_names = [f"ovos-pkg-{i}" for i in range(20)]
        many_descs = [f"desc {i}" for i in range(20)]
        mock_get.return_value.text = self._html_response(
            many_names, many_descs
        )
        results = list(search_pip("ovos", strict=False, max_results=5))
        self.assertLessEqual(len(results), 5)

    @patch("ovos_plugin_manager.installation.requests.get")
    def test_empty_response_yields_nothing(self, mock_get):
        from ovos_plugin_manager.installation import search_pip
        # Minimal HTML with no real packages (only the sentinel entries that
        # the split logic skips)
        mock_get.return_value.text = (
            '<span class="package-snippet__name">ONLY</span>'
            '<p class="package-snippet__description">ONLY</p>'
        )
        results = list(search_pip("nonexistent", strict=False))
        self.assertEqual(results, [])


class TestPipException(unittest.TestCase):
    def test_is_runtime_error(self):
        exc = PipException("pip failed")
        self.assertIsInstance(exc, RuntimeError)

    def test_message(self):
        exc = PipException("something went wrong")
        self.assertIn("something went wrong", str(exc))
