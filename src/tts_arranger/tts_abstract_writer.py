from abc import ABC, abstractmethod
from typing import Optional


class TTS_Abstract_Writer(ABC):
    def __init__(self, preferred_speakers: Optional[list[str]] = None) -> None:
        self.preferred_speakers = preferred_speakers or []
        self.sample_rate: int
