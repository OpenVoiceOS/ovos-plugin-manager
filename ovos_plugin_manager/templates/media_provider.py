"""Base class for MediaProvider plugins.

A ``MediaProvider`` is a media *catalog/search* plugin — the in-process
replacement for the old OCP search skills (``OVOSCommonPlaybackSkill`` +
``@ocp_search``). The OCP pipeline loads providers, hands each one the query
``Signals`` plus the request :class:`QueryContext`, and collects the
``Release`` candidates they return.

The whole contract is **one method**::

    search(signals, context) -> list[Release]

A provider that cannot serve the query (wrong media type, the device can't render
it, a blocked genre, no network/API key, …) simply returns an empty list — there
is no separate availability/routing/gating API to implement. The provider reads
:class:`QueryContext` (device capabilities + content policy + locale) to skip
work or tailor results; the pipeline filters/ranks across providers and wraps the
call so one provider raising cannot abort a multi-provider search.

Stream extraction is unchanged: a ``Release.uri`` may be a ``"{sei}//{uri}"``
deferred stream resolved at playback by the existing ``opm.ocp.extractor`` plugins.
"""
from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, Iterable, List, Optional, Set

if TYPE_CHECKING:
    # mediavocab is an optional dependency: opm only needs it for type hints here.
    from mediavocab import Release, Signals


def _values(items: Iterable) -> Set[str]:
    """Normalise an iterable of enums-or-strings to a set of string values."""
    return {getattr(x, "value", x) for x in (items or ())}


@dataclass
class QueryContext:
    """The environment a media search runs in.

    Device capabilities + content policy + locale — the information OCP search
    skills never received. The pipeline builds it from the session and passes it
    to every :meth:`MediaProvider.search`; a provider reads it to skip itself
    (e.g. a video provider on an audio-only device) or tailor results
    (resolution, region availability). All fields are optional — an empty
    ``QueryContext`` is fully permissive.
    """

    #: PlaybackType *values* the device can render (e.g. ``{"audio", "video"}``).
    #: Empty ⇒ no device gate.
    supported_playback_types: Set[str] = field(default_factory=set)
    #: genre tags the content policy blocks (e.g. ``{"adult"}``).
    blocked_genres: Set[str] = field(default_factory=set)
    lang: str = "en-us"
    region: Optional[str] = None          # ISO 3166-1 alpha-2
    session_id: Optional[str] = None
    #: forward-compatible bag for capabilities not yet first-class.
    extras: dict = field(default_factory=dict)

    def allows_playback(self, playback_types: Iterable) -> bool:
        """True if the device can render at least one of ``playback_types``
        (or no device gate is set). Convenience for providers self-filtering."""
        if not self.supported_playback_types:
            return True
        return bool(_values(playback_types) & self.supported_playback_types)

    def allows_genres(self, genres: Iterable) -> bool:
        """True if none of ``genres`` is policy-blocked."""
        return not (self.blocked_genres & _values(genres))


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
    def search(self, signals: "Signals", context: "QueryContext") -> List["Release"]:
        """Return candidate playables for ``signals`` in ``context``.

        The single method a provider must implement. Given the query
        :class:`~mediavocab.Signals` and the request :class:`QueryContext`,
        return zero or more :class:`~mediavocab.Release` candidates (each ranked
        by its own ``match_confidence``). Return ``[]`` when this provider cannot
        serve the query/context — there is nothing else to override.
        """

    def shutdown(self) -> None:
        """Optional: release any resources the provider holds."""
