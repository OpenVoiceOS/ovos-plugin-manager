# Pre-release quirks

Behavior changes since the last stable release, newest first. This file is
reset at each stable release; entries that remove or deprecate behavior
become the deprecation ledger for the next semver cycle.

## 2.11.2a2

- Plugin entry-point discovery now imports `entry_points` from the standard
  library `importlib.metadata` unconditionally. The `importlib_metadata`
  backport and the `pkg_resources` fallback (deprecated by setuptools) are
  gone; `requires-python` is already `>=3.10`, where the stdlib module has
  always supported the `group=` keyword used here, so behavior is unchanged.

## 2.11.1a5

- `ChatEngine`'s built-in `stream_tokens`, `stream_sentences`, and
  `MultimodalChatEngine.stream_chat` now call a subclass's `continue_chat`
  override by keyword instead of positionally. A subclass that names or
  orders its `continue_chat` parameters differently from the base signature
  was previously fed silently wrong values by these wrappers; it now gets
  the correctly named argument regardless of declaration order.
- `ChatEngine.__init_subclass__` inspects a subclass's own `continue_chat`
  override at class-definition time and logs one `LOG.warning`, naming the
  class, if the override accepts neither a `tools` parameter nor `**kwargs`.
  The warning never raises, so a non-conforming plugin still loads; it will
  simply never receive tool definitions and silently ignore requests that
  require tool calling.

## 2.11.1a3

- `UtteranceTransformersService.transform` and `MetadataTransformersService.transform`
  no longer merge a transformer's returned context into itself. In-place
  transformers commonly return the same context object they were handed;
  merging that object into itself recursively walked identical nested
  mappings until `RecursionError`. The merge is now skipped whenever the
  returned object is the same object the transformer received, so caller
  context identity is preserved, including an empty dict passed in by the
  caller. A transformer that returns a distinct delta or replacement dict
  still gets merged as before.
- Debug logging in the transformer runners is gated behind a check of the
  active log level and uses lazy `%s` formatting, avoiding the cost of
  building a debug string when debug logging is disabled. The logged
  context is also redacted: the `session` key is stripped before logging
  because a serialized session can carry credentials.
