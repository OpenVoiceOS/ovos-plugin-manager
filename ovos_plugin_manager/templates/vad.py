import abc
import collections

from ovos_config import Configuration
from ovos_utils import classproperty
from ovos_utils.process_utils import RuntimeRequirements


class AudioFrame:
    """Represents a "frame" of audio data."""

    def __init__(self, audio: bytes, timestamp: float, duration: int):
        self.bytes = audio
        self.timestamp = timestamp
        self.duration = duration


class VADEngine:
    def __init__(self, config=None, sample_rate=None):
        self.config_core = Configuration()
        self.config = config or {}
        self.sample_rate = sample_rate or \
                           self.config_core.get("listener", {}).get("sample_rate", 16000)

        self.padding_duration_ms = self.config.get("padding_duration_ms", 300)
        self.frame_duration_ms = self.config.get("frame_duration_ms", 30)
        self.thresh = self.config.get("thresh", 0.8)
        self.num_padding_frames = int(self.padding_duration_ms / self.frame_duration_ms)

    @classproperty
    def runtime_requirements(self):
        """ skill developers should override this if they do not require connectivity
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

    def _frame_generator(self, audio: bytes):
        """Generates audio frames from PCM audio data.
        Takes the desired frame duration in milliseconds, the PCM data, and
        the sample rate.
        Yields Frames of the requested duration.
        """
        n = int(self.sample_rate * (self.frame_duration_ms / 1000.0) * 2)
        offset = 0
        timestamp = 0.0
        duration = (float(n) / self.sample_rate) / 2.0

        while offset + n <= len(audio):
            yield AudioFrame(audio[offset:offset + n], timestamp, duration)
            timestamp += duration
            offset += n

    def extract_speech(self, audio: bytes):
        """returns the audio data with speech only, removing all noise before and after speech"""
        # We use a deque for our sliding window/ring buffer.
        ring_buffer = collections.deque(maxlen=self.num_padding_frames)
        triggered = False
        is_speech = False
        voiced_frames = []

        for frame in self._frame_generator(audio):

            is_speech = not self.is_silence(frame.bytes)

            if not triggered:
                ring_buffer.append((frame, is_speech))
                num_voiced = len([f for f, speech in ring_buffer if speech])
                # If we're NOTTRIGGERED and more than 90% of the frames in
                # the ring buffer are voiced frames, then enter the
                # TRIGGERED state.
                if num_voiced > self.thresh * ring_buffer.maxlen:
                    triggered = True
                    # We want to yield all the audio we see from now until
                    # we are NOTTRIGGERED, but we have to start with the
                    # audio that's already in the ring buffer.
                    for f, s in ring_buffer:
                        voiced_frames.append(f)
                    ring_buffer.clear()
            else:
                # We're in the TRIGGERED state, so collect the audio data
                # and add it to the ring buffer.
                voiced_frames.append(frame)
                ring_buffer.append((frame, is_speech))
                num_unvoiced = len([f for f, speech in ring_buffer if not speech])

                # If more than 90% of the frames in the ring buffer are
                # unvoiced, then enter NOTTRIGGERED and yield whatever
                # audio we've collected.
                if num_unvoiced > self.thresh * ring_buffer.maxlen:
                    return b''.join([f.bytes for f in voiced_frames])

    @abc.abstractmethod
    def is_silence(self, chunk):
        # return True or False
        return False

    def reset(self):
        pass
