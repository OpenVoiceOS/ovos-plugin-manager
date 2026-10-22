# Configuration Utilities

`ovos_plugin_manager.utils.config` has helpers to resolve plugin configuration from the
global OVOS config (`ovos.conf` / `mycroft.conf`), filter language-specific options, and
sort them by priority.

## `get_plugin_config`

```python
def get_plugin_config(
    config: Optional[dict] = None,
    section: str = None,
    module: Optional[str] = None,
) -> dict
```

Resolve a merged configuration dict for a plugin. Configuration precedence, highest to lowest:

1. Module-specific block: `config[section][module]`
2. Section-level defaults: `config[section]` (scalar keys only)
3. Top-level `lang`: `config['lang']`

**Parameters**

| Name | Type | Description |
|---|---|---|
| `config` | `dict` | Base configuration to parse. Defaults to `Configuration()`. |
| `section` | `str` | Top-level config key for the plugin category (e.g. `"stt"`, `"tts"`, `"hotwords"`). |
| `module` | `str` | Plugin entry point name to look up inside `config[section]`. If omitted, reads from `config[section]['module']`. |

**Returns** `dict`: merged config with at least `module` and `lang` keys, except for the
`hotwords`, `VAD`, `listener`, and `gui` sections.

**Example**

```python
from ovos_plugin_manager.utils.config import get_plugin_config

cfg = get_plugin_config(section="stt", module="ovos-stt-plugin-whisper")
# {'module': 'ovos-stt-plugin-whisper', 'lang': 'en-US', ...}
```

---

## `load_plugin_configs`

```python
def load_plugin_configs(
    plug_name: str,
    plug_type: Optional[PluginConfigTypes] = None,
    normalize_language_keys: bool = False,
) -> Union[dict, list]
```

Load language and variant configuration for a single plugin by calling its `.config` entry
point.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `plug_name` | `str` | Plugin entry point name (e.g. `"ovos-tts-plugin-piper"`). |
| `plug_type` | `PluginConfigTypes` | Config entry point group (e.g. `PluginConfigTypes.TTS`). |
| `normalize_language_keys` | `bool` | Standardize dict keys to BCP-47 format via `langcodes`. |

**Returns** `dict` of `{lang: [list_of_config_dicts]}` or `list`.

---

## `load_configs_for_plugin_type`

```python
def load_configs_for_plugin_type(plug_type: PluginTypes) -> dict
```

Load configs for all installed plugins of the given type.

**Returns** `{plugin_name: {lang: [configs]}}`.

---

## `get_plugin_language_configs`

```python
def get_plugin_language_configs(
    plug_type: PluginTypes,
    lang: str,
    include_dialects: bool = False,
) -> dict
```

Return configs for all plugins of `plug_type` that support `lang`.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `plug_type` | `PluginTypes` | Plugin category to search. |
| `lang` | `str` | BCP-47 language code (e.g. `"en-US"`). |
| `include_dialects` | `bool` | If `True`, also include configs for other dialects of the same macro-language. |

**Returns** `{plugin_name: [list_of_valid_config_dicts]}`.

---

## `get_plugin_supported_languages`

```python
def get_plugin_supported_languages(plug_type: PluginTypes) -> dict
```

Return a mapping of language code to list of plugin names that support that language.

**Returns** `{lang: [plugin_name, ...]}`.

---

## `sort_plugin_configs`

```python
def sort_plugin_configs(configs: dict) -> dict
```

Sort each plugin's config list by the `"priority"` key. Lower values mean higher priority.
The function removes invalid or empty config lists.

**Returns** `{plugin_name: [sorted_configs]}`.

---

## `get_valid_plugin_configs`

```python
def get_valid_plugin_configs(
    configs: dict,
    lang: str,
    include_dialects: bool,
) -> list
```

Filter a single plugin's `{lang: [configs]}` dict to configs that match `lang`.
When `include_dialects=True`, the result also includes configs for closely related
dialects, with a +15 priority bonus.

---

## Config priority

Within a config list, entries are sorted by their `"priority"` key. Higher values mean a
more preferred config. Factory methods iterate through the list from the end, so the
highest-priority entry runs last.

The default priority is `60`. A dialect match adds `15` to reach `75`, so it wins over a
generic language match at the default priority.

---

[← Writing a Plugin](writing-plugins.md) · [Home](index.md) · [Transformers →](transformers.md)

