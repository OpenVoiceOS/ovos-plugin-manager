import os
import sys
from os.path import exists, dirname
from subprocess import PIPE, Popen
from typing import Iterator, List, Optional, Tuple

import requests
from combo_lock import NamedLock
from ovos_utils.log import LOG

from ovos_plugin_manager.exceptions import PipException

# default constraints to use if none are given
DEFAULT_CONSTRAINTS = '/etc/mycroft/constraints.txt'
PIP_LOCK = NamedLock("ovos_pip.lock")


def search_pip(query: str, strict: bool = True,
               page: int = 1, max_results: int = 10) -> Iterator[Tuple[str, str]]:
    """
    Yield package name and short description pairs from PyPI search results.

    Searches pypi.org/search, parses result pages, and yields up to `max_results`
    tuples of `(package_name, description)`. Follows additional result pages automatically.

    Parameters:
        query (str): Search term to query on PyPI.
        strict (bool): If True, only include packages whose name contains `query`.
        page (int): Starting page number; intended for internal recursive pagination.
        max_results (int): Maximum total results to yield.

    Returns:
        Iterator[Tuple[str, str]]: Tuples of `(package_name, description)`.
    """
    raw_text = requests.get(f'https://pypi.org/search/?q={query}&page='
                            f'{page}').text
    raw_names = raw_text.split('<span class="package-snippet__name">')[1:-2]
    names = []
    for name in raw_names:
        names.append(name.split('</span>')[0])

    raw_desc = raw_text.split('<p class="package-snippet__description">')[1:-2]
    descs = []
    for desc in raw_desc:
        descs.append(desc.split('</p>')[0])

    n_results = 0
    if strict:
        pkgs = [(names[i], descs[i]) for i in range(len(names)) if
                query in names[i]]
    else:
        pkgs = [(names[i], descs[i]) for i in range(len(names))]
    for p in pkgs[:max_results]:
        yield p
    if len(pkgs) > max_results or not len(pkgs):
        return

    raw_pages = raw_text.split(f'<a href="/search/?q={query}&amp;page=')[1:-1]
    for idx, p in enumerate(raw_pages):
        try:
            p = p.split('button-group__button">')[-1].split('</a>')[0]
            raw_pages[idx] = int(p)
        except:
            raw_pages[idx] = 0
    next_page = bool(len([p for p in raw_pages if p > page]))

    if next_page:
        for pkg in search_pip(query, strict, page + 1):
            n_results += 1
            yield pkg
            if n_results >= max_results:
                return


def pip_install(packages: List[str], constraints: Optional[str] = None,
                print_logs: bool = False) -> bool:
    """
    Install pip package specifiers sequentially into the current Python interpreter.

    Uses an optional constraints file (falls back to ``DEFAULT_CONSTRAINTS`` if present).
    Serializes installs with a named lock. Prefixes with ``sudo -n`` when the interpreter
    bin directory is not writable.

    Parameters:
        packages (List[str]): Pip install specifiers (e.g. ``["ovos-tts-plugin-piper>=0.1"]``).
        constraints (Optional[str]): Path to a constraints file; if given and missing, returns
            False. If omitted and ``DEFAULT_CONSTRAINTS`` exists, it is used automatically.
        print_logs (bool): If True, forward pip stdout/stderr to the terminal.

    Returns:
        bool: True if all packages installed successfully; False if no packages given or the
        specified constraints file was not found.

    Raises:
        PipException: If any package installation exits with a non-zero status.
    """
    if not len(packages):
        return False
    # Use constraints to limit the installed versions
    if constraints and not exists(constraints):
        LOG.error('Couldn\'t find the constraints file')
        return False
    elif exists(DEFAULT_CONSTRAINTS):
        constraints = DEFAULT_CONSTRAINTS

    can_pip = os.access(dirname(sys.executable), os.W_OK | os.X_OK)
    pip_args = [sys.executable, '-m', 'pip', 'install']
    if constraints:
        pip_args += ['-c', constraints]

    if not can_pip:
        pip_args = ['sudo', '-n'] + pip_args

    with PIP_LOCK:
        """
        Iterate over the individual Python packages and
        install them one by one to enforce the order specified
        in the manifest.
        """
        for dependent_python_package in packages:
            LOG.info("(pip) Installing " + dependent_python_package)
            pip_command = pip_args + [dependent_python_package]
            if print_logs:
                proc = Popen(pip_command)
            else:
                proc = Popen(pip_command, stdout=PIPE, stderr=PIPE)
            pip_code = proc.wait()
            if pip_code != 0:
                stderr = proc.stderr.read().decode()
                raise PipException(
                    pip_code, proc.stdout.read().decode(), stderr
                )

    return True
