"""Base class for MediaProvider plugins.

A ``MediaProvider`` is a media *catalog/search* plugin. It replaces the old
OCP search skills (``OVOSCommonPlaybackSkill`` + ``@ocp_search``): instead of
broadcasting ``ovos.common_play.query`` over the bus and waiting for skills to
answer, the OCP pipeline loads providers in-process, gates them by routing, and
calls :meth:`search` directly.

Routing mirrors :class:`mediavocab.models.protocols.MetadataProvider` — the
same **three-axis** gate (``media`` / ``playback_type`` / ``genre_filter``) — so
the pipeline can skip providers that cannot serve a query before paying for a
search. The contract differs in one way: a metadata *resolver* returns a single
best identity match, while media *discovery* returns many candidate playables,
so :meth:`search` returns a ``list`` of :class:`mediavocab.Release`.

Providers are also **context-aware** in a way OCP skills never were: the
pipeline gates them with :meth:`MediaProvider.serves` against a
:class:`QueryContext` (device capabilities + content policy + locale), so a
video provider is skipped on an audio-only device and an ``adult`` provider is
skipped when the content filter blocks it — *before* any search runs.

Stream extraction is unchanged: a provider returns ``Release`` objects whose
``uri`` may be a ``"{sei}//{uri}"`` deferred stream resolved at playback by the
existing ``opm.ocp.extractor`` plugins.
"""
from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, Iterable, List, Optional, Set

from ovos_utils.log import LOG

if TYPE_CHECKING:
    # mediavocab is an optional dependency: opm only needs it for type hints here
    # (the routing primitives live downstream in the plugins that subclass this).
    from mediavocab import MediaType, Release, Signals
    from mediavocab.taxonomy import PlaybackType


def _values(items: Iterable) -> Set[str]:
    """Normalise an iterable of enums-or-strings to a set of string values."""
    return {getattr(x, "value", x) for x in (items or ())}


@dataclass
class QueryContext:
    """The requesting environment a media search runs in.

    This is what makes a ``MediaProvider`` **context-aware** — the information
    OCP search skills never received. The OCP pipeline builds it from the
    session (device capabilities, the user's content policy, language/region)
    and the pipeline gates providers on it (:meth:`MediaProvider.serves`) so a
    provider the device or policy cannot use is never searched. Providers may
    also read it to tailor results (e.g. resolution, region availability).

    All fields are optional; an empty :class:`QueryContext` is fully permissive.
    """

    #: PlaybackType *values* the device can render (e.g. ``{"audio", "video"}``).
    #: Empty ⇒ no device gate (assume the device can play anything).
    supported_playback_types: Set[str] = field(default_factory=set)
    #: genre tags the policy blocks (e.g. ``{"adult"}`` from the content filter).
    blocked_genres: Set[str] = field(default_factory=set)
    lang: str = "en-us"
    region: Optional[str] = None          # ISO 3166-1 alpha-2
    session_id: Optional[str] = None
    #: forward-compatible bag for capabilities not yet first-class.
    extras: dict = field(default_factory=dict)

    def allows_playback(self, playback_types: Iterable) -> bool:
        """True if the device can render at least one of ``playback_types``."""
        if not self.supported_playback_types:
            return True
        return bool(_values(playback_types) & self.supported_playback_types)

    def allows_genres(self, genres: Iterable) -> bool:
        """True if none of ``genres`` is policy-blocked."""
        return not (self.blocked_genres & _values(genres))


class MediaProvider(metaclass=ABCMeta):
    """Base class for all media catalog/search providers.

    Subclasses declare their routing via the three class-level sets and
    implement :meth:`is_available` and :meth:`search`. The default
    :meth:`matches` reuses mediavocab's canonical three-axis routing gate.

    Arguments:
        config (dict): configuration dict for the instance.
    """

    name: ClassVar[str] = ""
    """Stable provider name — the registry key and ``skill_id`` downstream."""

    media: ClassVar[Set[MediaType]] = set()
    """Media-type gate. Empty ⇒ universal."""

    playback_type: ClassVar[Set[PlaybackType]] = set()
    """Playback-type gate (AUDIO/VIDEO/PAGED/INTERACTIVE). Empty ⇒ universal.
    Note: this is ``mediavocab.taxonomy.PlaybackType``, distinct from
    ``ovos_utils.ocp.PlaybackType`` (the backend selector); the two are bridged
    in the pipeline/player, not here."""

    genre_filter: ClassVar[Set[str]] = set()
    """Genre-tag gate (``mediavocab.taxonomy.genre``). Empty ⇒ no gate."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}

    @abstractmethod
    def is_available(self) -> bool:
        """True if the provider has everything it needs to run now
        (API keys, optional deps, network reachability)."""

    @abstractmethod
    def search(self, signals: Signals, lang: str = "en-us") -> List[Release]:
        """Return zero or more candidate playables for ``signals``.

        Results carry their own ranking via ``Release.match_confidence``
        (``0.0``–``1.0``); the pipeline filters and ranks across providers.
        """

    def featured_media(self, lang: str = "en-us") -> List[Release]:
        """Optional curated/home content. Default: empty."""
        return []

    def matches(self, signals: "Signals") -> bool:
        """Three-axis routing test (mediavocab spec). Override only if the
        default ``(media, playback_type, genre_filter)`` gate is wrong for this
        provider.

        Imports mediavocab lazily: a provider subclass that reaches this default
        already depends on mediavocab, but opm itself must not require it."""
        from mediavocab.models.protocols import provider_matches
        return provider_matches(self, signals)

    def serves(self, signals: "Signals",
               context: Optional[QueryContext] = None) -> bool:
        """Context-aware routing gate — what the pipeline should gate on.

        Returns ``True`` only when the provider both *matches* the query
        (three-axis :meth:`matches`) **and** the requesting :class:`QueryContext`
        can actually use it:

        * the device can render at least one of the provider's ``playback_type``s
          (so a video-only provider is skipped on an audio-only device), and
        * none of the provider's ``genre_filter`` tags is policy-blocked
          (so an ``adult`` provider is skipped when the content filter blocks it).

        ``context=None`` ⇒ fully permissive (equivalent to :meth:`matches`).
        """
        if not self.matches(signals):
            return False
        if context is None:
            return True
        if self.playback_type and not context.allows_playback(self.playback_type):
            return False
        if self.genre_filter and not context.allows_genres(self.genre_filter):
            return False
        return True

    def search_context(self, signals: "Signals",
                       context: Optional[QueryContext] = None,
                       lang: str = "en-us") -> List[Release]:
        """Context-aware search. The default ignores *context* and delegates to
        :meth:`search`; providers that tailor results to the device/policy
        (resolution, region availability, …) override this."""
        return self.search(signals, lang=lang)

    def shutdown(self):
        """Release any resources held by the provider."""

    def search_safe(self, signals: Signals,
                    context: Optional[QueryContext] = None,
                    lang: str = "en-us") -> List[Release]:
        """Call :meth:`search_context`, never raising. Returns ``[]`` on error.

        Used by the pipeline's thread-pool dispatch so one misbehaving
        provider cannot abort a multi-provider search.
        """
        try:
            return self.search_context(signals, context=context, lang=lang) or []
        except Exception:
            LOG.exception(f"MediaProvider '{self.name or self.__class__.__name__}' "
                          f"search failed")
            return []
