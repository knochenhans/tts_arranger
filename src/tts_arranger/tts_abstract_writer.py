from abc import ABC, abstractmethod
from typing import Optional

from .items.tts_item import TTS_Item  # type: ignore
from loguru import logger


class TTS_Abstract_Writer(ABC):
    """
    An abstract base class for TTS writers.
    """

    def __init__(
        self,
        project: dict,
    ) -> None:
        """
        Initialize a new TTS_Abstract_Writer instance.

        :param preferred_speakers: A list of preferred speaker names for multi-speaker models to be used instead of the available speakers of the selected model.
                                If set to None, the default speaker(s) will be used.
        :type preferred_speakers: Optional[list[str]]

        :return: None
        """
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
            logger.info(f"Synthesizing item {current_nr + 1} of {max_nr}")
        else:
            logger.info(f"Adding pause: {current_item.length}ms")
