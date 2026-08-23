# Pre-release quirks

Behavior changes since the last stable release, newest first. This file is
reset at each stable release; entries that remove or deprecate behavior
become the deprecation ledger for the next semver cycle.

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
