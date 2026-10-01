# Language Plugins — Translation & Detection

**Translation entry point:** `opm.lang.translate`
**Detection entry point:** `opm.lang.detect`
**Template:** `ovos_plugin_manager.templates.language`
**Factory:** `ovos_plugin_manager.language`

---

## `LanguageTranslator` base class

```python
from ovos_plugin_manager.templates.language import LanguageTranslator
```

### Constructor

```python
LanguageTranslator(
    internal_language: Optional[str] = None,
    config: Optional[dict] = None,
)
```

| Attribute | Description |
|---|---|
| `default_language` | The translator's primary working language (BCP-47). |
| `config` | Plugin-specific config. |

### Abstract method (must implement)

#### `translate(text: str, target: Optional[str] = None, source: Optional[str] = None) -> str`

Translate `text` from `source` language to `target` language. Both default to
`self.default_language` if omitted.

### Provided methods

#### `detect(text: str) -> str`

Detect the language of `text`. Default implementation raises `NotImplementedError`.

---

## `LanguageDetector` base class

```python
from ovos_plugin_manager.templates.language import LanguageDetector
```

### Abstract method (must implement)

#### `detect(text: str) -> str`

Return the BCP-47 language code detected in `text`.

#### `detect_proba(text: str) -> dict`

Return `{lang: probability}` for all detected languages.

---

## Factory classes (`ovos_plugin_manager.language`)

### `OVOSLangTranslationFactory`

```python
from ovos_plugin_manager.language import OVOSLangTranslationFactory

translator = OVOSLangTranslationFactory.create()
translated = translator.translate("Hallo Welt", target="en", source="de")
```

### `OVOSLangDetectionFactory`

```python
from ovos_plugin_manager.language import OVOSLangDetectionFactory

detector = OVOSLangDetectionFactory.create()
lang = detector.detect("Hello world")  # "en"
```

---

## Configuration

```json
{
  "language": {
    "detection_module": "ovos-lang-detect-plugin-fastlangid",
    "translation_module": "ovos-translate-plugin-nllb",
    "ovos-translate-plugin-nllb": {
      "model": "facebook/nllb-200-distilled-600M"
    }
  }
}
```
