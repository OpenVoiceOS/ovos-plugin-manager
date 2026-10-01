# AUDIT.md — ovos-plugin-manager

_Last updated: 2026-03-11 by Claude Sonnet 4.6_

---

## Critical (Bugs / Correctness)

### `ovos_plugin_manager/utils/__init__.py:194–196` — Dead log branch after dict assignment
`find_plugins` loads the entry point at line 194 (`entrypoints[entry_point.name] = entry_point.load()`), then immediately checks `if entry_point.name not in entrypoints` on line 195 — a condition that can never be True at that point because the key was just inserted. The debug log on line 196 is therefore unreachable dead code.

### `ovos_plugin_manager/utils/config.py:85` — `valid_configs` appended incorrectly for exact-match branch
In `get_valid_plugin_configs`, when `include_dialects=False` and the language is found (line 83), `valid_configs.append(configs[lang])` appends the entire list stored at that key rather than extending with its items. If downstream code iterates expecting individual config dicts, it will receive a one-element list containing another list, causing `KeyError` or `TypeError` at runtime.

### `ovos_plugin_manager/stt.py:91` — Bare `assert` used as validation guard
`get_stt_config` uses `assert stt_config.get('lang') is not None` to validate the lang key. Assertions are disabled when Python is run with the `-O` (optimise) flag (`python -O`). Any production deployment using optimised mode silently skips this check and passes an invalid config downstream.

### `ovos_plugin_manager/tts.py:174–177` — `get_voices` iterates a directory that may not exist
`get_voices` calls `os.listdir(VOICES_FOLDER)` without checking whether the directory exists first (unlike `scan_voices`, which calls `os.makedirs`). If `scan=False` and the XDG voice config directory has never been created, this raises `FileNotFoundError` and the function returns nothing to the caller with no warning.

### `ovos_plugin_manager/wakewords.py:160–164` — `get_wws` iterates a directory that may not exist
Same pattern as `get_voices`: `os.listdir(WW_FOLDER)` is called without checking whether `WW_FOLDER` exists. `scan_wws` always raises `NotImplementedError`, so `scan=True` silently swallows the error and then crashes on `os.listdir`.

### `ovos_plugin_manager/templates/tts.py:362–364` — `validate_ssml` discards return value
`validate_ssml` calls `self.format_speak_tags(utterance, False)` and `self.format_speak_tags(utterance)` but neither result is captured or returned. The utterance is not modified; the calls are effectively no-ops. The final `return utterance.replace("  ", " ")` returns the original (unformatted) utterance, which means SSML wrapping/stripping logic in `format_speak_tags` never has effect.

### `ovos_plugin_manager/templates/tts.py:690–695` — Silent exception in `stop()`
```python
try:
    TTS.playback.stop()
except Exception as e:
    pass
```
Swallows all exceptions including `KeyboardInterrupt` (inherited from `BaseException` but not `Exception`) and resource-leak errors. The caught variable `e` is unused. At minimum, log the exception.

### `ovos_plugin_manager/templates/tts.py:149–150` — Class-level mutable state shared across instances
`TTS.queue = None` and `TTS.playback = None` are class attributes. The first `TTS.__init__` call that runs sets `TTS.queue = Queue()`, mutating the class. Subsequent instances share the same queue and playback object. This is intentional for the audio pipeline but not documented, and any subclass that needs independent state will silently share the singleton queue.

### `ovos_plugin_manager/templates/vad.py:104–141` — `extract_speech` returns `None` implicitly
`extract_speech` returns a `bytes` object only if the unvoiced threshold is crossed. If the audio ends without triggering the NOTTRIGGERED exit, the function returns `None`. Callers (e.g. in `ovos-dinkum-listener`) that do `b"".join(...)` on the result will get `TypeError: can only join an iterable`. The return type annotation says `bytes` but `None` is possible.

### `ovos_plugin_manager/installation.py:103–104` — Constraints logic can silently override caller
If the caller passes `constraints=None`, the code falls through to `elif exists(DEFAULT_CONSTRAINTS): constraints = DEFAULT_CONSTRAINTS`. This is reasonable. However, if the caller passes a valid constraints path but `DEFAULT_CONSTRAINTS` also exists, the `elif` is skipped but the caller's path is still used — but if the caller passes an invalid path (non-existent), the code returns `False` at line 102 before reaching the `elif`. This means the caller can never opt out of the default constraints if their file doesn't exist; the error is misleading.

### `ovos_plugin_manager/plugin_entry.py:183–194` — `plugin_type` infers from string that may already be a `PluginTypes` enum
In `OpenVoiceOSPlugin.plugin_type`, when `self._data.get("plugin_type")` is a `PluginTypes` enum member, calling `.lower()` on it (line 185) works because `PluginTypes` extends `str`, but the subsequent `if "tts" in self._plugtype.lower()` may match multiple enum values (e.g. both `TTS` and `TTS_TRANSFORMER`), causing the wrong type to be assigned.

### `ovos_plugin_manager/utils/config.py:105` — Bare `except:` swallows all errors in `sort_plugin_configs`
```python
try:
    configs[plug_name] = sorted(...)
except:
    LOG.exception(...)
```
`except:` (no type) catches `SystemExit`, `KeyboardInterrupt`, and `GeneratorExit` in addition to normal exceptions. Should be `except Exception`.

---

## Performance

### `ovos_plugin_manager/plugin_entry.py:197–251` — `plugin_type` property calls `find_*_plugins()` on every access
`OpenVoiceOSPlugin.plugin_type` is a non-cached property. Every call to it invokes `find_stt_plugins()`, `find_tts_plugins()`, `find_wake_word_plugins()`, `find_audio_service_plugins()` — each of which iterates all installed entry points. Since `plugin_type` is accessed from `load()` → `clazz` → `is_installed` → `json` in a tight chain, a single `plugin.json` call triggers four separate full plugin scans. The result is cached in `self._plugtype` only after the first full determination, but the chain before that can be expensive.

### `ovos_plugin_manager/utils/__init__.py:184–206` — `find_plugins` uses a module-level list for error tracking
`find_plugins._errored` is a plain Python list. Membership checks use `if entry_point not in find_plugins._errored`, which is O(n). Over time this list grows unbounded as more broken plugins are encountered. Use a `set` instead.

### `ovos_plugin_manager/utils/__init__.py:273` — `_iter_entrypoints._warnings` is a growing list with O(n) membership checks
Same issue as above: `if e.name not in _iter_entrypoints._warnings` is O(n) on a list that grows unbounded. Should be a `set`.

### `ovos_plugin_manager/tts.py:138–155` — `scan_voices` calls `get_tts_supported_langs()` then `get_tts_lang_configs()` in nested loops, each scanning all plugins
`get_tts_supported_langs()` already iterates all plugins and all their configs. Then `get_tts_lang_configs(lang)` does the same again for each language. The full plugin scan runs O(languages × plugins) times. These should share a single pass.

### `ovos_plugin_manager/templates/tts.py:211–216` — `plugin_id` property scans all TTS plugins on every access
`TTS.plugin_id` iterates `find_tts_plugins()` — a full entry-point scan — every time `self._plugin_id` is empty. When a plugin is loaded via `OVOSTTSFactory.create`, `_plugin_id` is set immediately after. But any plugin loaded outside the factory will trigger repeated scans on every call to `execute` → `_get_ctxt` → `self.plugin_id`.

### `ovos_plugin_manager/templates/embeddings.py:219–496` — `distance()` is a 270-line if/elif chain with repeated numpy imports inside branches
`spearman_rank`, `wasserstein`, `kendall_tau` perform `from scipy.stats import ...` inside the elif branch on every call. These should be top-level imports (or at least module-level lazy imports) to avoid repeated import overhead in hot paths.

### `ovos_plugin_manager/utils/tts_cache.py:58–72` — `_get_cache_entries` materializes generators then iterates again
Two generator expressions are chained and then consumed. Fine for moderate file counts, but the third generator is returned as a lazy generator to `_delete_oldest`, which then `sorted()` it — materializing the entire thing. No issue unless cache directories become very large, but worth documenting.

---

## Type Annotation Gaps

### `ovos_plugin_manager/utils/__init__.py:174` — `find_plugins` parameter type too broad
`plug_type: PluginTypes = None` — the default `None` means the function accepts `None`, `PluginTypes`, or anything else (lines 187–190 show `str` and arbitrary iterables are accepted). Signature should be `Optional[Union[PluginTypes, Iterable[PluginTypes]]] = None`.

### `ovos_plugin_manager/utils/__init__.py:276` — `load_plugin` return type missing
`load_plugin` has no return type annotation. It returns the loaded entry point object (usually a class) or `None`. Should be `Optional[Type]`.

### `ovos_plugin_manager/utils/config.py:57` — `get_valid_plugin_configs` return type annotation partially wrong
Declared as returning `list` but the function returns `list[dict]` specifically. More precise: `List[Dict[str, Any]]`.

### `ovos_plugin_manager/utils/config.py:116–134` — `load_plugin_configs` return type is `Union[dict, list]`
The actual return is whatever the underlying plugin config entry point returns, which is either `dict` (lang → list[config]) or `None` (if `load_plugin` returns `None`). Returning `None` when the caller expects `dict` or `list` can cause `AttributeError` on `.items()`. Should be `Optional[Dict]`.

### `ovos_plugin_manager/templates/tts.py:152–153` — `__init__` parameters lack type annotations
`config`, `validator`, `ssml_tags` parameters in `TTS.__init__` are untyped. Should be `Optional[dict]`, `Optional[TTSValidator]`, `Optional[List[str]]`.

### `ovos_plugin_manager/templates/tts.py:270–283` — `modify_tag` and `handle_metric` missing parameter/return types
`modify_tag(self, tag)` — no annotation on `tag` or return. `handle_metric(self, metadata=None)` — no annotation. Should be `(self, tag: str) -> str` and `(self, metadata: Optional[dict] = None) -> None`.

### `ovos_plugin_manager/templates/tts.py:625–649` — `viseme` return type annotation wrong
Declared implicitly as returning `list` or `None` via `return visimes or None`. Callers must handle `None`. Return type should be `Optional[List[Tuple[str, float]]]`.

### `ovos_plugin_manager/templates/vad.py:104` — `extract_speech` return type incorrect
Annotated as `bytes` but can return `None`. Should be `Optional[bytes]`.

### `ovos_plugin_manager/templates/transformers.py:33` — `MetadataTransformer.transform` return annotation is a tuple expression, not a real type
`def transform(self, context: dict = None) -> (list, dict):` — Python interprets `(list, dict)` as a tuple of type objects, not `Tuple[list, dict]`. The correct annotation is `-> dict` (the function only returns a dict). Same issue at `UtteranceTransformer.transform` line 68 `-> (list, dict)`, which returns `Tuple[List[str], dict]`.

### `ovos_plugin_manager/templates/agents.py:228–278` — `stream_tokens` / `stream_sentences` use space-split as sentence boundary
`stream_tokens` does `yield from self.continue_chat(...).content.split()` — splitting on whitespace yields individual words, not tokens. `stream_sentences` does `.split("\n")` — newline-split yields entire paragraphs, not sentences. Both defaults are misleading and wrong for real streaming use cases. These are labelled "Default implementation" in the docstring but the semantics differ from what the method names promise.

### `ovos_plugin_manager/thirdparty/solvers.py:27` — `__init__` parameter `config` lacks `Dict` import annotation
`config=None` has no type hint. Should be `Optional[Dict[str, Any]] = None`.

### `ovos_plugin_manager/templates/embeddings.py:27` — `EmbeddingsDB.__init__` parameter annotation missing `Optional`
`def __init__(self, config: Dict[str, Any] = None)` — `None` is a valid value but `Optional[Dict[str, Any]]` is not stated. Same for `TextEmbedder`, `ImageEmbedder`, `FaceEmbedder`, `VoiceEmbedder` at lines 501, 522, 544, 567.

### `ovos_plugin_manager/wakewords.py:171` — `OVOSWakeWordFactory.get_class` return annotation is `type` not `Type[HotWordEngine]`
`-> type` is too broad. Should be `-> Optional[Type[HotWordEngine]]`.

---

## Code Smells / Debt

### `ovos_plugin_manager/utils/__init__.py:209–239` — Dual `_iter_plugins` implementations with no shared interface
Two versions of `_iter_plugins` (one using `importlib_metadata`, one using `pkg_resources`) are defined inside a `try/except ImportError` block. `pkg_resources` is deprecated in Python 3.12+. The fallback should be documented and eventually removed. Both implementations are missing return type annotations.

### `ovos_plugin_manager/templates/solvers.py:15–18` — Module-level `log_deprecation` call executes on import
The deprecated module fires a deprecation warning at import time, which will appear in logs even for code that imports the module only to check availability. This is intentional but noisy and should be documented in the module's deprecation timeline.

### `ovos_plugin_manager/templates/tts.py:681` — `RANT` comment in production code
Line 681: `# RANT: why do you hate strings ChrisV?` — informal comment inappropriate for production codebase. Should be a `# TODO` or simply removed.

### `ovos_plugin_manager/installation.py:35–70` — `search_pip` scrapes PyPI HTML, not the JSON API
`search_pip` parses raw HTML from `pypi.org/search` using string splits. This is fragile: any change to PyPI's HTML structure silently breaks results. The PyPI JSON API (`https://pypi.org/pypi/{package}/json`) or `pip search` (deprecated) would be more stable. Additionally, no timeout is set on the `requests.get` call at line 35 — a slow PyPI response will block indefinitely.

### `ovos_plugin_manager/installation.py:114–133` — `pip_install` has a docstring inside the `with` block
Lines 115–119 contain a multi-line string literal inside a `with PIP_LOCK:` block. This is parsed as a statement expression (a bare string), not a docstring. It looks like a docstring but has no effect and wastes cognitive overhead. Should be a `#` comment.

### `ovos_plugin_manager/plugin_entry.py:183–255` — `plugin_type` property is 70+ lines with six cascading inference steps
The property performs six sequential heuristic checks. Each check has four elif branches for tts/stt/wakeword/audio. This is 24 near-identical string-in-name checks. Extract to a helper `_infer_plugin_type_from_string(s: str) -> Optional[PluginTypes]` to eliminate duplication.

### `ovos_plugin_manager/templates/tts.py:346` — `format_speak_tags` uses `lstrip`/`rstrip` incorrectly for tag removal
Line 346: `to_speak.lstrip("<speak>").rstrip("</speak>")`. `lstrip` and `rstrip` strip individual *characters* from a set, not substrings. `lstrip("<speak>")` strips any leading combination of `<`, `s`, `p`, `e`, `a`, `k`, `>` characters — not the literal tag. This is a latent bug that may corrupt speech text beginning with those characters.

### `ovos_plugin_manager/utils/ui.py:233–237` — `get_plugin_options` accesses `entry["plugin_name"]` which may not exist
`config2option` puts `"plugin_name"` (not just `"engine"`) into the dict (line 69: `"plugin_name": plugin_display_name`). But in `get_plugin_options` at line 234, `plugs[engine]["plugin_name"]` is accessed only after checking `engine not in plugs`, so the first iteration is fine — but if the key is absent from the opt dict, it will `KeyError`. The opt dict is built from `config2option` which does include `"plugin_name"`, so this is likely not a runtime issue, but the assumption is implicit.

### `ovos_plugin_manager/templates/solvers.py:276` — Bare `except:` silently drops `get_data` exceptions
```python
try:
    data = _call_with_sanitized_kwargs(self.get_data, ...)
except:
    return {}
```
A plugin's `get_data` raising any exception (including `SystemExit`) causes `search` to silently return an empty dict. Should be `except Exception as e: LOG.exception(e); return {}`.

### `ovos_plugin_manager/ocp.py:71` — Bare `except:` in `OVOSOCPFactory.load`
Plugin load errors are caught with bare `except:` and only `LOG.error` is called (no traceback). Should use `LOG.exception` and `except Exception`.

### `ovos_plugin_manager/skills.py:174` — Bare `except:` in `load_skill_plugins`
Same pattern: bare `except:` swallows all errors including `SystemExit`.

### `ovos_plugin_manager/templates/audio.py:257` — Bare `except:` silences metadata extractor import error
```python
try:
    from ovos_ocp_files_plugin.plugin import OCPFilesMetadataExtractor
    return OCPFilesMetadataExtractor.extract_metadata(uri)
except:
    ...
```
Catches `ImportError` and any other error including `AttributeError` from a broken plugin. Should be `except ImportError` for the optional dependency and `except Exception` for the extraction call, logged separately.

### `ovos_plugin_manager/templates/tts.py:346` (see also) — `include_tags=False` path in `format_speak_tags` is broken
`to_speak.lstrip("<speak>").rstrip("</speak>")` (line 346) does character-set stripping, not substring removal. The correct idiom would be `to_speak.removeprefix("<speak>").removesuffix("</speak>")` (Python 3.9+).

### `ovos_plugin_manager/utils/config.py:28` — Double `Configuration()` call on every `get_plugin_config` invocation
Line 28: `config = config or Configuration()` and then line 28 again: `lang = standardize_lang_tag(config.get('lang') or Configuration().get('lang', "en"))`. If the caller passes no config, `Configuration()` is instantiated twice. The second call is particularly wasteful because `config` already holds the result of the first.

### `ovos_plugin_manager/templates/coreference.py:89,99` — Commented-out `print()` debug statements
Two `# print(...)` lines remain as debug artefacts.

### `ovos_plugin_manager/templates/embeddings.py:211–496` — `distance()` method is 285 lines and should be split
The `distance` method contains 30+ elif branches, each implementing a different metric. This violates the single-responsibility principle and makes the method untestable in isolation. Each metric should be a standalone function or registered via a dictionary dispatch table.

### `ovos_plugin_manager/templates/g2p.py:82–91` — Lambda defined inside function body for normalisation
Lines 82–91 define `norm = lambda k: k.replace("9", "").replace(...)` — a lambda chain that strips digit suffixes. This is used in only one place. While not wrong, a named helper function would be clearer and testable.

### `ovos_plugin_manager/utils/tts_cache.py:93` — Exception silently swallowed in `_delete_oldest`
```python
try:
    os.remove(path)
    ...
except Exception:
    pass
```
If a file removal fails (permissions, locked file on Windows), it silently continues without logging. The freed space counter is not updated, so the cache curation may believe it freed more space than it did.

### Magic strings throughout — plugin type strings duplicated
The string `"pocketsphinx"` appears as a hardcoded default at `wakewords.py:222`. The string `"ovos-tts-plugin-dummy"` appears at `tts.py:196`. These should be named constants.

---

## Style / Convention Violations

### `ovos_plugin_manager/utils/__init__.py:111` — Missing blank line before `PluginConfigTypes` class definition
PEP 8 requires two blank lines between top-level class definitions. Only one blank line separates `PluginTypes` and `PluginConfigTypes` (line 111).

### `ovos_plugin_manager/templates/transformers.py:33,68` — Return annotation syntax wrong
`-> (list, dict)` is syntactically valid Python but semantically a tuple of type objects, not `Tuple[list, dict]`. This will mislead static type checkers.

### `ovos_plugin_manager/templates/tts.py:193–200` — Missing blank line between `lang` property and setter
The `@lang.setter` is defined on line 197 with no blank line after the `@property` body, violating PEP 8.

### `ovos_plugin_manager/templates/agents.py:228` — Inconsistent indentation in `stream_tokens` definition
`stream_tokens` is indented with 4 extra spaces on the `session_id` and subsequent parameters (lines 229–231), creating hanging indent inconsistency relative to the rest of the class.

### `ovos_plugin_manager/thirdparty/solvers.py:1` — BSD-3 licensed file inside an Apache-2.0 repository
`thirdparty/solvers.py` carries a BSD-3 license header. The repo is Apache-2.0. Both licenses are permissive and compatible, but the mixed license must be documented. The `# TODO - delete this file` comment at line 1 confirms this file is planned for removal.

### `ovos_plugin_manager/templates/tts.py:445` — Double `##` comment markers used as section separators
Lines like `## synth`, `## cache`, `## shutdown` use non-standard double-hash markers. While not a PEP 8 violation, this is inconsistent with the rest of the codebase and can confuse documentation parsers.
