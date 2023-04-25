from abc import ABC, abstractmethod
from typing import Optional

from .items.tts_item import TTS_Item  # type: ignore
from .utils.log import LOG_TYPE, bcolors, log  # type: ignore


class TTS_Abstract_Writer(ABC):
    def __init__(self, preferred_speakers: Optional[list[str]] = None) -> None:
        self.preferred_speakers = preferred_speakers or []
        self.sample_rate: int

    def print_progress(self, current_nr: int, max_nr: int, current_item: TTS_Item):
        if current_item.text:
            log(LOG_TYPE.INFO, f'Synthesizing item {current_nr + 1} of {max_nr}:{bcolors.ENDC}')
        else:
            log(LOG_TYPE.INFO, f'Adding pause: {current_item.length}ms:{bcolors.ENDC}')