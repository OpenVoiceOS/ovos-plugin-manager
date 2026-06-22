"""Base class for MediaProvider plugins.

A ``MediaProvider`` is a media *catalog/search* plugin. It replaces the old
OCP search skills (``OVOSCommonPlaybackSkill`` + ``@ocp_search``): instead of
broadcasting ``ovos.common_play.query`` over the bus and waiting for skills to
answer, the OCP pipeline loads providers in-process, gates them by routing, and
calls :meth:`search` directly.

Routing mirrors :class:`mediavocab.models.protocols.MetadataProvider` — the
same **three-axis** gate (``media`` / ``modality`` / ``genre_filter``) — so the
pipeline can skip providers that cannot serve a query before paying for a
search. The contract differs in one way: a metadata *resolver* returns a single
best identity match, while media *discovery* returns many candidate playables,
so :meth:`search` returns a ``list`` of :class:`mediavocab.Release`.

Stream extraction is unchanged: a provider returns ``Release`` objects whose
``uri`` may be a ``"{sei}//{uri}"`` deferred stream resolved at playback by the
existing ``opm.ocp.extractor`` plugins.
"""
from abc import ABCMeta, abstractmethod
from typing import ClassVar, List, Optional, Set

from ovos_utils.log import LOG

from mediavocab import MediaType, Release, Signals
from mediavocab.taxonomy import PlaybackModality
from mediavocab.models.protocols import provider_matches


class MediaProvider(metaclass=ABCMeta):
    """Base class for all media catalog/search providers.

    Subclasses declare their routing via the three class-level sets and
    implement :meth:`is_available` and :meth:`search`. The default
    :meth:`matches` reuses mediavocab's canonical three-axis gate.

    Arguments:
        config (dict): configuration dict for the instance.
    """

    name: ClassVar[str] = ""
    """Stable provider name — the registry key and ``skill_id`` downstream."""

    media: ClassVar[Set[MediaType]] = set()
    """Media-type gate. Empty ⇒ universal."""

    modality: ClassVar[Set[PlaybackModality]] = set()
    """Playback-modality gate (AUDIO/VIDEO/INTERACTIVE/TEXT). Empty ⇒ universal."""

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

    def matches(self, signals: Signals) -> bool:
        """Three-axis routing test (mediavocab spec axiom 13). Override
        only if the default ``(media, modality, genre_filter)`` gate is
        wrong for this provider."""
        return provider_matches(self, signals)

    def shutdown(self):
        """Release any resources held by the provider."""

    def search_safe(self, signals: Signals, lang: str = "en-us") -> List[Release]:
        """Call :meth:`search`, never raising. Returns ``[]`` on error.

        Used by the pipeline's thread-pool dispatch so one misbehaving
        provider cannot abort a multi-provider search.
        """
        try:
            return self.search(signals, lang=lang) or []
        except Exception:
            LOG.exception(f"MediaProvider '{self.name or self.__class__.__name__}' "
                          f"search failed")
            return []
