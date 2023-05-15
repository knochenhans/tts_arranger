
from typing import Callable, Optional

import mammoth

from tts_arranger.tts_reader.checker import Checker  # type: ignore

from .. import TTS_Project  # type: ignore
from .tts_html_based_reader import TTS_HTML_Based_Reader  # type: ignore


class TTS_Docx_Reader(TTS_HTML_Based_Reader):
    """
    Class for converting a docx file into a TTS project.
    """

    def __init__(self, ignore_default_checkers=False, custom_checkers: Optional[list[Checker]] = None):
        super().__init__(custom_checkers, ignore_default_checkers=ignore_default_checkers)

    def load(self, filename: str, callback: Optional[Callable[[float], None]] = None) -> None:
        """"
        Load a docx file into the TTS_Project.

        :param filename: The filename of the docx file.
        :type filename: str

        :param callback: The callback function for progress updates.
        :type callback: Optional[Callable[[float], None]]

        :return: None
        """
        super().load(filename, callback)

        with open(filename, "rb") as docx_file:
            style_map = """
            p[style-name^='Heading'] => h1:fresh
            p[style-name^='Title'] => h1:fresh
            p[style-name^='Subtitle'] => h1:fresh
            p[style-name^='Sub Title'] => h1:fresh
            """
            result = mammoth.convert_to_html(docx_file, style_map=style_map)
            self.html_converter.add_from_html(result.value)

            self.project = self.html_converter.get_project()
            self.project.clean_empty_chapters()

            # Use first item as chapter and document title
            title = self.project.tts_chapters[0].tts_items[0].text
            self.project.tts_chapters[0].title = title
            self.project.title = title
