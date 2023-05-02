from typing import Optional

from .. import TTS_Chapter  # type: ignore
from ..tts_html_converter import (CHECKER_SIGNAL, Checker,  # type: ignore
                                  CheckerItemProperties, TTS_HTML_Converter)
from .tts_abstract_reader import TTS_Abstract_Reader  # type: ignore


class TTS_HTML_Based_Reader(TTS_Abstract_Reader):
    """
    Base class for converting an EPUB file into a TTS project.
    """

    def __init__(self, preferred_speakers: Optional[list[str]] = None, custom_checkers: Optional[list[Checker]] = None, custom_checkers_files: Optional[list[str]] = None, ignore_default_checkers=False):
        """
        :param preferred_speakers: Optional list of preferred speakers to use instead of the models predefined speaker list  
        :type preferred_speakers: Optional[list[str]]
        """
        super().__init__(preferred_speakers)

        self.current_properties: list[CheckerItemProperties] = []
        self.default_properties = CheckerItemProperties(0, 250)
        self.last_signal = CHECKER_SIGNAL.NO_SIGNAL
        self.current_chapter: Optional[TTS_Chapter] = None

        self.html_converter = TTS_HTML_Converter(custom_checkers=custom_checkers, custom_checkers_files=custom_checkers_files, ignore_default_checkers=ignore_default_checkers)

    # def initialize_checkers(self, default_properties: Optional[CheckerItemProperties] = None, checker_config_file='', checkers: Optional[list[Checker]] = None, ignore_default=False):
    #     self.default_properties = default_properties or self.default_properties
    #     self.current_properties.append(self.default_properties)

    #     self.checkers = checkers or []
    #     self.html_converter = TTS_HTML_Converter(checkers=self.checkers)
    #     self.html_converter.add_checkers_from_json(checker_config_file, ignore_default=ignore_default)
