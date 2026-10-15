from dataclasses import dataclass
from typing import Optional, Tuple

from ovos_utils import classproperty
from ovos_utils.process_utils import RuntimeRequirements

from ovos_config import Configuration


@dataclass(frozen=True)
class EndOfTurnDecision:
    """The result of feeding one audio chunk to an :class:`EndOfTurnEngine`.

    Attributes:
        p_end: Probability that the user has finished their turn.
        p_speech: Probability that the user is speaking, if the engine reports
            it; ``None`` otherwise.
        ended: ``True`` when ``p_end`` crossed the engine's threshold for this
            chunk.
    """

    p_end: float
    p_speech: Optional[float] = None
    ended: bool = False


@dataclass(frozen=True)
class ChunkContext:
    """What the listener already knows about a chunk, when it offers it.

    The listener computes a VAD verdict for every chunk. An engine that decides
    from speech activity reads it here instead of running a second detector, so
    the engine and the listener agree on one silence criterion. An engine that
    reads the raw audio ignores this.

    Attributes:
        is_speech: The listener's VAD verdict for this chunk, or ``None`` when
            the listener does not provide it.
    """

    is_speech: Optional[bool] = None


class EndOfTurnEngine:
    """End-of-turn detection base class.

    An end-of-turn engine answers "has the user finished their turn?" from the
    audio alone, and updates that answer as more audio arrives. This is
    distinct from :class:`~ovos_plugin_manager.templates.vad.VADEngine`, which
    only reports whether the current frame contains speech.

    Engines are fed every chunk of microphone audio captured while a command
    may be in progress. :meth:`update` is called once per chunk and the engine
    is free to re-frame internally, so chunks are not required to be any fixed
    size. Audio is 16-bit signed PCM, mono, at ``sample_rate``.

    The base class is a no-op engine: :meth:`get_probability` always returns
    ``0.0``, so :meth:`is_end_of_turn` never fires. A listener that loads it
    (or that has no plugin configured) keeps whatever end-of-turn logic it
    already owns, such as a silence timer.
    """

    #: primary BCP-47 language subtags the engine supports; empty means all
    supported_langs: Tuple[str, ...] = ()

    def __init__(self, config: Optional[dict] = None,
                 sample_rate: Optional[int] = None):
        """
        Initialize the end-of-turn engine.

        Parameters:
            config (Optional[dict]): Plugin configuration. Recognized key:
                - "threshold" (float): p_end above which the turn is considered
                  finished (default 0.5).
            sample_rate (Optional[int]): Audio sample rate in Hz. If omitted,
                reads the core configuration "listener.sample_rate" or defaults
                to 16000.
        """
        self.config_core = Configuration()
        self.config = config or {}
        self.sample_rate = sample_rate or \
            self.config_core.get("listener", {}).get("sample_rate", 16000)
        self.threshold = self.config.get("threshold", 0.5)

    @classproperty
    def runtime_requirements(cls):
        """skill developers should override this if they do not require connectivity
         some examples:
         IOT plugin that controls devices via LAN could return:
            scans_on_init = True
            RuntimeRequirements(internet_before_load=False,
                                 network_before_load=scans_on_init,
                                 requires_internet=False,
                                 requires_network=True,
                                 no_internet_fallback=True,
                                 no_network_fallback=False)
         online search plugin with a local cache:
            has_cache = False
            RuntimeRequirements(internet_before_load=not has_cache,
                                 network_before_load=not has_cache,
                                 requires_internet=True,
                                 requires_network=True,
                                 no_internet_fallback=True,
                                 no_network_fallback=True)
         a fully offline plugin:
            RuntimeRequirements(internet_before_load=False,
                                 network_before_load=False,
                                 requires_internet=False,
                                 requires_network=False,
                                 no_internet_fallback=True,
                                 no_network_fallback=True)
        """
        return RuntimeRequirements(internet_before_load=False,
                                   network_before_load=False,
                                   requires_internet=False,
                                   requires_network=False,
                                   no_internet_fallback=True,
                                   no_network_fallback=True)

    def update(self, chunk: bytes,
               context: Optional["ChunkContext"] = None) -> EndOfTurnDecision:
        """Feed a chunk of audio and get the current decision.

        Parameters:
            chunk (bytes): 16-bit PCM, mono, at ``sample_rate``. Size is not
                fixed; the engine handles re-framing.
            context (Optional[ChunkContext]): what the listener already knows
                about this chunk, such as its VAD verdict. Optional; an engine
                that reads the raw audio ignores it.

        Returns:
            EndOfTurnDecision: probabilities and the boolean decision for this
                chunk.
        """
        p_end = self.get_probability(chunk, context)
        return EndOfTurnDecision(p_end=p_end,
                                 p_speech=self.p_speech,
                                 ended=p_end >= self.threshold)

    def get_probability(self, chunk: bytes,
                        context: Optional["ChunkContext"] = None) -> float:
        """Return the probability the user has finished their turn.

        Subclasses override this with their model. The default returns ``0.0``,
        which means "never fires".

        Parameters:
            chunk (bytes): 16-bit PCM, mono, at ``sample_rate``.
            context (Optional[ChunkContext]): the listener's per-chunk context,
                when it provides one.

        Returns:
            float: probability in ``[0.0, 1.0]``.
        """
        return 0.0

    @property
    def p_speech(self) -> Optional[float]:
        """Probability the user is speaking, if the engine reports it."""
        return None

    def is_end_of_turn(self, chunk: bytes,
                       context: Optional["ChunkContext"] = None) -> bool:
        """Feed a chunk and return only the boolean decision."""
        return self.update(chunk, context).ended

    def reset(self):
        """Reset any internal state. Called when a new user turn starts."""
        pass
