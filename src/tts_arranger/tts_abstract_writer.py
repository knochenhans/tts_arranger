from abc import ABC, abstractmethod
from typing import Optional

from .items.tts_item import TTS_Item  # type: ignore
from .utils.log import LOG_TYPE, bcolors, log  # type: ignore


class TTS_Abstract_Writer(ABC):
    """
    An abstract base class for TTS writers.
    """
    def __init__(self, preferred_speakers: Optional[list[str]] = None) -> None:
        """
        Initialize a new TTS_Abstract_Writer instance.

        :param preferred_speakers: A list of preferred speaker names for multi-speaker models to be used instead of the available speakers of the selected model.
                                If set to None, the default speaker(s) will be used.
        :type preferred_speakers: Optional[list[str]]

        :return: None
        """
        self.preferred_speakers = preferred_speakers or []
        self.sample_rate: int

    def print_progress(self, current_nr: int, max_nr: int, current_item: TTS_Item):
        """
        Print synthesizing progress information for the TTS writer.

        :param current_nr: The current TTS item number.
        :type current_nr: int

        :param max_nr: The total number of TTS items.
        :type max_nr: int

        :param current_item: The current TTS item being synthesized.
        :type current_item: TTS_Item

        :return: None
        """
        if current_item.text:
            log(LOG_TYPE.INFO, f'Synthesizing item {current_nr + 1} of {max_nr}:{bcolors.ENDC}')
        else:
            log(LOG_TYPE.INFO, f'Adding pause: {current_item.length}ms:{bcolors.ENDC}')