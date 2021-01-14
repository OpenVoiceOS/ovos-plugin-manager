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
#
"""Common functions for loading plugins."""
import requests
import pkg_resources
from enum import Enum
from ovos_utils.log import LOG
from os.path import exists, join, dirname
import os
import sys
from subprocess import PIPE, Popen
from ovos_plugin_manager.exceptions import PipException
from json_database.utils.combo_lock import ComboLock
from tempfile import gettempdir

# default constraints to use if none are given
DEFAULT_CONSTRAINTS = '/etc/mycroft/constraints.txt'
PIP_LOCK = ComboLock(join(gettempdir(), "ovos_pip.lock"))


class PluginTypes(str, Enum):
    AUDIO = 'mycroft.plugin.audioservice'
    STT = 'mycroft.plugin.stt'
    TTS = 'mycroft.plugin.tts'
    WAKEWORD = 'mycroft.plugin.wake_word'


def find_plugins(plug_type=None):
    """Finds all plugins matching specific entrypoint type.

    Arguments:
        plug_type (str): plugin entrypoint string to retrieve

    Returns:
        dict mapping plugin names to plugin entrypoints
    """
    entrypoints = {}
    if not plug_type:
        plugs = list(PluginTypes)
    elif isinstance(plug_type, str):
        plugs = [plug_type]
    else:
        plugs = plug_type
    for plug in plugs:
        for entry_point in pkg_resources.iter_entry_points(plug):
            entrypoints[entry_point.name] = entry_point.load()
    return entrypoints


def load_plugin(plug_name, plug_type=None):
    """Load a specific plugin from a specific plugin type.

    Arguments:
        plug_type: (str) plugin type name. Ex. "mycroft.plugin.tts".
        plug_name: (str) specific plugin name

    Returns:
        Loaded plugin Object or None if no matching object was found.
    """
    plugins = find_plugins(plug_type)
    if plug_name in plugins:
        return plugins[plug_name]
    LOG.warning('Could not find the plugin {}.{}'.format(
        plug_type or "all plugin types", plug_name))
    return None


def search_pip(query, strict=True, page=1, max_results=10):
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


def pip_install(packages, constraints=None, print_logs=False):
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
