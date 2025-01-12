from typing import Callable, List, Optional

from bs4 import BeautifulSoup, PageElement  # type: ignore

from tts_arranger.items.tts_chapter import TTS_Chapter
from tts_arranger.items.tts_item import TTS_Item
from tts_arranger.items.tts_project import TTS_Project
from tts_arranger.tts_reader.tts_abstract_reader import TTS_Abstract_Reader  # type: ignore


class TTS_HTML_Based_Reader(TTS_Abstract_Reader):
    from tts_arranger.tts_reader.checker import Checker

    """
    Base class for converting an EPUB file into a TTS project.
    """

    def __init__(
        self,
        custom_checkers: Optional[list[Checker]] = None,
        custom_checkers_files: Optional[list[str]] = None,
        ignore_default_checkers=False,
    ):
        """
        Initializes the reader and its HTML converter

        :param custom_checkers: An optional list of custom checkers
        :type custom_checkers: Optional[list[Checker]], optional

        :param custom_checkers_files: An optional list of paths to files containing custom checkers
        :type custom_checkers_files: Optional[list[str]], optional

        :param ignore_default_checkers: Defines if the default checkers should be ignored, defaults to False
        :type ignore_default_checkers: bool, optional
        """
        super().__init__()

        from tts_arranger.tts_reader.checker import (
            CHECKER_SIGNAL,
            CheckerItemProperties,
        )
        from tts_arranger.tts_html_converter import TTS_HTML_Converter

        self.current_properties: list[CheckerItemProperties] = []
        self.default_properties = CheckerItemProperties("0", 250)
        self.last_signal = CHECKER_SIGNAL.NO_SIGNAL
        self.current_chapter: Optional[TTS_Chapter] = None

        self.html_converter = TTS_HTML_Converter(
            custom_checkers=custom_checkers,
            custom_checkers_files=custom_checkers_files,
            ignore_default_checkers=ignore_default_checkers,
        )

    def load_raw(
        self,
        content: str,
        author: str = "",
        title: str = "",
        callback: Optional[Callable[[float], None]] = None,
    ) -> None:
        """
        Load HTML content and write converted content into the TTS_Project.

        :param content: The HTML string.
        :type content: str

        :param author: The author of the HTML file (will be used as the author of the audiobook).
        :type author: str

        :param title: The title of the HTML file (will be used as the title of the audiobook).
        :type title: str

        :param callback: An optional function that takes a float between 0 and 1 representing the progress of the loading process as its argument. This can be used to periodically check on the loading progress. Defaults to None if not provided.
        :type callback: Optional[Callable[[float], None]]

        :return: None
        """
        super().load_raw(content, author, title, callback)

        soup = BeautifulSoup(content, "html.parser")
        chapter_title = None

        if isinstance(soup, PageElement):
            self.project = self.html_converter.convert_from_html_to_project(str(soup))

            # Get titles from first chapter items
            if isinstance(self.project, TTS_Project):
                self.project.get_titles()

                # self.project.merge_from_project(project)

                # Get chapter title from title tag
                if soup.title:
                    chapter_title = soup.title.string

                # Set title for added chapters
                # TODO: Figure out how to handle multiple added chapters
                if chapter_title is not None:
                    self.project.tts_chapters[-1].title = chapter_title

                self.project.author = self.author
                self.project.title = self.title
