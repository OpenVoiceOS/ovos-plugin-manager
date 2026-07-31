# Installation Utilities

`ovos_plugin_manager.installation` has helpers to install plugins at runtime with `pip`,
and to search PyPI for OVOS-compatible packages.

## `pip_install`

```python
def pip_install(
    packages: list,
    constraints: Optional[str] = None,
    print_logs: bool = False,
) -> bool
```

Install one or more Python packages with the current interpreter's `pip`. The function
installs packages in the order given.

If the current user cannot write to the interpreter binary, the function tries
`sudo -n pip install` automatically.

A named lock (`ovos_pip.lock`) serializes concurrent calls, so parallel plugin installers
do not race each other.

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

Search PyPI for packages that match `query`. The function scrapes `pypi.org/search`.

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

The `OpenVoiceOSPlugin` class (see `ovos_plugin_manager.plugin_entry`) wraps `pip_install`:

```python
from ovos_plugin_manager.plugin_entry import OpenVoiceOSPlugin

p = OpenVoiceOSPlugin({"package_name": "ovos-stt-plugin-whisper"})
p.install()  # calls pip_install(["ovos-stt-plugin-whisper"])
```

If `package_name` is not set but a GitHub `url` is present, the plugin installs with
`pip install git+<url>`.

---

## `PipException`

`pip_install` raises this error when a package fails to install.

```python
from ovos_plugin_manager.exceptions import PipException
```

`PipException` subclasses `RuntimeError`. The error message includes the pip exit code and
stderr.

---

[Home](index.md) · [Plugin Types →](plugin-types.md)
