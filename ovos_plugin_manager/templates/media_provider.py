"""Base class for MediaProvider plugins.

A ``MediaProvider`` is a media *catalog/search* plugin — the in-process
replacement for the old OCP search skills (``OVOSCommonPlaybackSkill`` +
``@ocp_search``). The OCP pipeline loads providers and asks each one to search.

The whole contract is **one method**::

    search(signals, lang="en-us", **context) -> list[Release]

``signals`` is the query (a :class:`mediavocab.Signals`); ``lang`` + ``**context``
describe the request environment the pipeline knows about (e.g.
``supported_playback_types``, ``blocked_genres``, ``region``, ``session_id``) — a
provider reads whichever kwargs it cares about and ignores the rest. A provider
that cannot serve the query (wrong media, the device can't render it, a blocked
genre, no network/API key, …) just returns an empty list. There is nothing else
to implement: availability and routing are the provider's own concern.

Stream extraction is unchanged: a ``Release.uri`` may be a ``"{sei}//{uri}"``
deferred stream resolved at playback by the existing ``opm.ocp.extractor`` plugins.
"""
from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, ClassVar, List, Optional

if TYPE_CHECKING:
    # mediavocab is an optional dependency: opm only needs it for type hints here.
    from mediavocab import Release, Signals


class MediaProvider(metaclass=ABCMeta):
    """A media catalog/search provider. Subclass and implement :meth:`search`.

    Args:
        config: instance configuration dict.
    """

    name: ClassVar[str] = ""
    """Stable provider name — the registry key and ``skill_id`` downstream."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}

    @abstractmethod
    def search(self, signals: "Signals", lang: str = "en-us",
               **context) -> List["Release"]:
        """Return candidate playables for ``signals``.

        The single method a provider must implement. ``signals`` is the query;
        ``lang`` and any ``**context`` kwargs the pipeline passes
        (``supported_playback_types``, ``blocked_genres``, ``region``,
        ``session_id``, …) describe the request environment — use what you need,
        ignore the rest. Return zero or more :class:`~mediavocab.Release`
        candidates (each ranked by its own ``match_confidence``), or ``[]`` when
        this provider cannot serve the query.
        """

    def shutdown(self) -> None:
        """Optional: release any resources the provider holds."""
