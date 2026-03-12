# Installation Utilities

`ovos_plugin_manager.installation` provides helpers for installing plugins at runtime via
`pip` and for searching PyPI for OVOS-compatible packages.

## `pip_install`

```python
def pip_install(
    packages: list,
    constraints: Optional[str] = None,
    print_logs: bool = False,
) -> bool
```

Install one or more Python packages using the current interpreter's `pip`. Packages are
installed sequentially in the order given.

If the interpreter binary is not writable by the current user, `sudo -n pip install` is
attempted automatically.

A named lock (`ovos_pip.lock`) serializes concurrent calls so that parallel plugin
installers do not race.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `packages` | `list[str]` | Package specifiers passed directly to `pip install` (e.g. `["ovos-tts-plugin-piper>=0.1"]`). |
| `constraints` | `str` | Path to a pip constraints file. Falls back to `/etc/mycroft/constraints.txt` if that file exists. |
| `print_logs` | `bool` | If `True`, pip output is printed to stdout/stderr; otherwise it is captured. |

**Returns** `True` on success.

**Raises** `PipException` if any package fails to install.

**Example**

```python
from ovos_plugin_manager.installation import pip_install

pip_install(["ovos-stt-plugin-whisper"])
```

---

## `search_pip`

```python
def search_pip(
    query: str,
    strict: bool = True,
    page: int = 1,
    max_results: int = 10,
) -> Iterator[Tuple[str, str]]
```

Search PyPI for packages matching `query` by scraping `pypi.org/search`.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `query` | `str` | Search term. |
| `strict` | `bool` | If `True` (default), only packages whose name contains `query` are returned. |
| `page` | `int` | Starting page (used internally for pagination). |
| `max_results` | `int` | Maximum total results to yield. |

**Yields** `(package_name, description)` tuples.

**Example**

```python
from ovos_plugin_manager.installation import search_pip

for name, desc in search_pip("ovos-tts-plugin", max_results=5):
    print(name, "-", desc)
```

---

## `OpenVoiceOSPlugin.install`

The `OpenVoiceOSPlugin` class (see `ovos_plugin_manager.plugin_entry`) wraps `pip_install`
for convenience:

```python
from ovos_plugin_manager.plugin_entry import OpenVoiceOSPlugin

p = OpenVoiceOSPlugin({"package_name": "ovos-stt-plugin-whisper"})
p.install()  # calls pip_install(["ovos-stt-plugin-whisper"])
```

If `package_name` is not set but a GitHub `url` is present, it installs via
`pip install git+<url>`.

---

## `PipException`

Raised by `pip_install` when a package fails to install.

```python
from ovos_plugin_manager.exceptions import PipException
```

Subclasses `RuntimeError`. The error message includes the pip exit code and stderr.
