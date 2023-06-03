import abc

from dataclasses import dataclass
from typing import Optional


@dataclass
class Microphone:
    sample_rate: int = 16000
    sample_width: int = 2
    sample_channels: int = 1
    chunk_size: int = 4096

    @property
    def frames_per_chunk(self) -> int:
        return self.chunk_size // (self.sample_width * self.sample_channels)

    @property
    def seconds_per_chunk(self) -> float:
        return self.frames_per_chunk / self.sample_rate

    @abc.abstractmethod
    def start(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def read_chunk(self) -> Optional[bytes]:
        raise NotImplementedError()

    @abc.abstractmethod
    def stop(self):
        raise NotImplementedError()

