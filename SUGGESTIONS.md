# SUGGESTIONS.md — ovos-plugin-manager

> Evidence-backed proposals from full source code audit (2026-03-11).
> Each entry references the specific file and line that motivates the change.

---

## 1. Fix `validate_ssml` to actually use the return value of `format_speak_tags`

**Problem**: `TTS.validate_ssml` (templates/tts.py:362–364) calls `self.format_speak_tags(utterance, False)` and `self.format_speak_tags(utterance)` but discards both return values. The SSML wrapping/stripping logic therefore has no effect; the raw `utterance` is returned unchanged.

**Fix**: Assign the return value:
```python
if not self.ssml_tags or "speak" not in self.ssml_tags:
    utterance = self.format_speak_tags(utterance, False)
elif self.ssml_tags and "speak" in self.ssml_tags:
    utterance = self.format_speak_tags(utterance)
```

**Impact**: High — correctness bug. All SSML handling in `TTS.execute` is silently broken.

---

## 2. Replace `lstrip`/`rstrip` with `removeprefix`/`removesuffix` in `format_speak_tags`

**Problem**: `format_speak_tags` line 346 uses `to_speak.lstrip("<speak>").rstrip("</speak>")`. `lstrip`/`rstrip` strip individual characters from a character set, not substrings. Text beginning with the characters `<`, `s`, `p`, `e`, `a`, `k`, `>` will be incorrectly mutilated.

**Fix**:
```python
return to_speak.removeprefix("<speak>").removesuffix("</speak>")
```
`removeprefix`/`removesuffix` are available since Python 3.9 and this package already requires Python 3.10+.

**Impact**: Medium — latent correctness bug; may manifest with SSML-heavy plugins.

---

## 3. Cache `plugin_type` resolution to avoid repeated full plugin scans

**Problem**: `OpenVoiceOSPlugin.plugin_type` (plugin_entry.py:197–251) calls `find_stt_plugins()`, `find_tts_plugins()`, `find_wake_word_plugins()`, `find_audio_service_plugins()` on each call to the property before `self._plugtype` is set. A single `plugin.json` access chains through `clazz` → `is_installed` → `plugin_type`, triggering four full entry-point scans.

**Fix**: After `self._plugtype` is determined (any branch), the result is already cached. The issue is that `self._plugtype` starts as `None` and the property must be fully re-evaluated to find it is still `None`. Document explicitly that once set `_plugtype` is never cleared, and add an early-return guard:
```python
if self._plugtype is not None:
    return self._plugtype
```
This is already the intent of line 183 (`if not self._plugtype`) — but the guard only short-circuits if a previous call completed. The fix is already implicit; the remaining issue is the first-access cost. Consider a dedicated `_discover_plugin_type()` method called once from `__init__` if `plugin_type` is provided.

**Impact**: Medium — performance. On systems with many installed plugins, first-time access is expensive.

---

## 4. Replace list-based error/warning sets with `set` in `find_plugins` and `_iter_entrypoints`

**Problem**: `find_plugins._errored` (utils/__init__.py:206) and `_iter_entrypoints._warnings` (utils/__init__.py:273) are plain `list` objects. Membership checks (`if x not in list`) are O(n). Both lists grow unbounded over the lifetime of the process.

**Fix**:
```python
find_plugins._errored = set()
# In find_plugins:
find_plugins._errored.add(entry_point)
```
```python
_iter_entrypoints._warnings = set()
# In _iter_entrypoints:
_iter_entrypoints._warnings.add(e.name)
```

**Impact**: Low effort, meaningful performance gain on systems with many broken plugins.

---

## 5. Add `Optional[bytes]` return type to `VADEngine.extract_speech`

**Problem**: `VADEngine.extract_speech` (templates/vad.py:104) returns `bytes` only if the unvoiced threshold is crossed. If the input audio ends before that, the function returns `None` implicitly. The current return annotation says `bytes`.

**Fix**: Change annotation to `Optional[bytes]` and add a docstring note:
```python
def extract_speech(self, audio: bytes) -> Optional[bytes]:
    """...Returns None if no speech segment was detected."""
```
Callers should guard: `result = vad.extract_speech(audio); if result: ...`.

**Impact**: Medium — prevents `TypeError` in downstream callers that concatenate or write the result.

---

## 6. Refactor the 6-step type-inference chain in `OpenVoiceOSPlugin.plugin_type` into a helper

**Problem**: The property at plugin_entry.py:183–255 is 70+ lines with six cascading inference steps and 24 near-identical string membership tests.

**Fix**: Extract:
```python
def _infer_plugin_type_from_string(s: str) -> Optional[PluginTypes]:
    s = s.lower()
    if "tts" in s:
        return PluginTypes.TTS
    elif "stt" in s:
        return PluginTypes.STT
    elif "word" in s:
        return PluginTypes.WAKEWORD
    elif "audio" in s:
        return PluginTypes.AUDIO
    return None
```
Then reduce the property to six calls to this helper.

**Impact**: Low effort — dramatically improves readability and reduces lines by ~40.

---

## 7. Add timeout to `search_pip` HTTP request and switch to PyPI JSON API

**Problem**: `installation.py:35` calls `requests.get(f'https://pypi.org/search/...')` with no timeout. A slow/hung PyPI server will block the caller indefinitely. The HTML scraping approach is also fragile.

**Fix**:
```python
response = requests.get(url, timeout=10)
```
Long term: use the PyPI JSON API (`https://pypi.org/pypi/{package}/json`) for structured data instead of HTML parsing.

**Impact**: Medium — prevents process hang; improves reliability.

---

## 8. Unify the four `find_X_plugins` / `load_X_plugin` pairs via a generic factory

**Problem**: `tts.py`, `stt.py`, `wakewords.py`, `audio.py`, `g2p.py`, `vad.py`, etc. each define the same two functions:
```python
def find_X_plugins() -> Dict[str, Type[X]]:
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.X)

def load_X_plugin(module_name: str) -> Type[X]:
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.X)
```
This pattern is duplicated ~12 times. A generic factory function would eliminate the boilerplate:
```python
def make_plugin_finder(plug_type: PluginTypes):
    def find():
        return find_plugins(plug_type)
    return find
```

**Impact**: Medium — reduces maintenance burden when new plugin types are added.

---

## 9. Replace `assert` with explicit validation in `get_stt_config`

**Problem**: `stt.py:91` uses `assert stt_config.get('lang') is not None` which is disabled under `-O` (optimised) Python.

**Fix**:
```python
if stt_config.get('lang') is None:
    raise ValueError("STT config missing required 'lang' key")
```

**Impact**: Low effort — correctness in optimised deployments.

---

## 10. Add disk-existence guard in `get_voices` and `get_wws`

**Problem**: `tts.py:174` and `wakewords.py:162` call `os.listdir(VOICES_FOLDER)` / `os.listdir(WW_FOLDER)` without checking directory existence, raising `FileNotFoundError` when voice/WW configs have never been scanned.

**Fix**: Guard with:
```python
if not os.path.isdir(VOICES_FOLDER):
    continue  # or return {}
```

**Impact**: Low — prevents crash on first run or clean install.

---

## 11. Decompose `EmbeddingsDB.distance` into a dispatch table

**Problem**: `templates/embeddings.py:211–496` has a 285-line `if/elif` chain with 30+ distance metrics. It is untestable in isolation, hard to extend, and imports `scipy.stats` conditionally inside branches.

**Fix**: Use a registry pattern:
```python
_METRICS: Dict[str, Callable] = {
    "cosine": _cosine_distance,
    "euclidean": _euclidean_distance,
    ...
}

def distance(self, a, b, metric="cosine", **kwargs) -> float:
    if metric not in _METRICS:
        raise ValueError(f"Unsupported metric: {metric}")
    return _METRICS[metric](a, b, **kwargs)
```
Move `scipy` imports to module level inside `try/except ImportError`.

**Impact**: Medium — makes individual metrics unit-testable and the method readable.

---

## 12. Log exceptions in `TTS.stop` instead of silently swallowing them

**Problem**: `templates/tts.py:690–695` catches `Exception` and does `pass`, discarding the error entirely. Resource leaks (e.g. unclosed audio device) will be invisible.

**Fix**:
```python
except Exception:
    LOG.exception("Error stopping TTS playback")
```

**Impact**: Low effort — greatly improves debuggability.

---

## 13. Upgrade bare `except:` to `except Exception` with logging across the codebase

**Problem**: Six locations use bare `except:` (skills.py:174, utils/config.py:105, ocp.py:71, installation.py:64, templates/solvers.py:276, templates/audio.py:257). This swallows `SystemExit`, `KeyboardInterrupt`, and `GeneratorExit`.

**Fix**: Replace all bare `except:` with `except Exception` and add `LOG.exception(...)` where not already present.

**Impact**: Low effort — prevents critical errors from being hidden during shutdown sequences.

---

## 14. Remove or formally delete `thirdparty/solvers.py` per its own TODO

**Problem**: `thirdparty/solvers.py` line 1 contains `# TODO - delete this file in next major release`. It carries a BSD-3 license header inconsistent with the rest of the repo (Apache-2.0), and `templates/solvers.py` fires a deprecation warning on import.

**Fix**: Schedule removal in the next major version bump. Until then, ensure `CHANGELOG.md` and `MAINTENANCE_REPORT.md` document the deprecation timeline clearly.

**Impact**: Low short-term — reduces code surface and license ambiguity.
