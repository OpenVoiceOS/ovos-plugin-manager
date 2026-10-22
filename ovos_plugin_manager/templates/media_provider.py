"""Base class for MediaProvider plugins.

A ``MediaProvider`` is a media *catalog/search* plugin — the in-process
replacement for the old OCP search skills (``OVOSCommonPlaybackSkill`` +
``@ocp_search``). The OCP pipeline loads providers and asks each one to search.

The whole contract is **one method**::

    search(signals, lang="en-us", *, supported_playback_types=None,
           blocked_genres=None, region=None, session_id=None) -> list[Release]

``signals`` is the query (a :class:`mediavocab.Signals`); the keyword arguments
describe the request environment the pipeline knows about — a provider reads
whichever it cares about and ignores the rest. A provider that cannot serve the
query (wrong media, the device can't render it, a blocked genre, no network/API
key, …) just returns an empty list. There is nothing else to implement:
availability and routing are the provider's own concern.

Stream extraction is unchanged: a ``Release.uri`` may be a ``"{sei}//{uri}"``
deferred stream resolved at playback by the existing ``opm.ocp.extractor`` plugins.
"""
from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, ClassVar, List, Optional, Set

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
    def search(self, signals: "Signals", lang: str = "en-us", *,
               supported_playback_types: Optional[Set[str]] = None,
               blocked_genres: Optional[Set[str]] = None,
               region: Optional[str] = None,
               session_id: Optional[str] = None) -> List["Release"]:
        """Return candidate playables for ``signals``.

        The single method a provider must implement.

        Args:
            signals: the query (:class:`mediavocab.Signals`).
            lang: BCP-47 language tag of the request.
            supported_playback_types: PlaybackType *values* the device can render
                (e.g. ``{"audio", "video"}``); ``None``/empty ⇒ no device gate.
            blocked_genres: genre tags the content policy blocks (e.g.
                ``{"adult"}``).
            region: ISO 3166-1 alpha-2 region of the request.
            session_id: originating session id.

        Returns zero or more :class:`~mediavocab.Release` candidates (each ranked
        by its own ``match_confidence``), or ``[]`` when this provider cannot
        serve the query.
        """

    def shutdown(self) -> None:
        """Optional: release any resources the provider holds."""
