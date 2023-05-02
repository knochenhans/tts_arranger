import base64
import datetime
import json
import os
from pathlib import Path
from typing import Callable, Optional

from bs4 import BeautifulSoup, PageElement  # type: ignore
from dateutil.parser import parse  # type: ignore
from ebooklib import ITEM_DOCUMENT, epub  # type: ignore

from tts_arranger.tts_reader.checker import Checker  # type: ignore

from .tts_html_based_reader import TTS_HTML_Based_Reader  # type: ignore


class TTS_EPUB_Reader(TTS_HTML_Based_Reader):
    """
    Class for converting an EPUB file into a TTS project.
    """

    def __init__(self, preferred_speakers: Optional[list[str]] = None, ignore_default_checkers=False, custom_checkers: Optional[list[Checker]] = None):
        """
        Initializes the reader

        :param preferred_speakers: Optional list of preferred speakers to use instead of the models predefined speaker list , defaults to None
        :type preferred_speakers: Optional[list[str]], optional

        :param ignore_default_checkers: Defines if the default checkers should be ignored, defaults to False
        :type ignore_default_checkers: bool, optional
        """
        super().__init__(preferred_speakers, custom_checkers, ignore_default_checkers=ignore_default_checkers)

    def get_chapter_title(self, toc: list, href: str) -> str:
        """
        Get the title of the chapter from the table of contents and href.

        :param toc: The table of contents.
        :type toc: list

        :param href: The href of the chapter.
        :type href: str

        :return: The title of the chapter.
        :rtype: str
        """

        for toc_item in toc:
            if isinstance(toc_item, epub.Link):
                if toc_item.href == href:
                    return toc_item.title
            elif isinstance(toc_item, tuple):
                if isinstance(toc_item[0], epub.Section):
                    if toc_item[0].href == href:
                        return toc_item[0].title
                if isinstance(toc_item[1], list):
                    title = self.get_chapter_title(toc_item[1], href)

                    if title:
                        return title
                    else:
                        pass
        return ''

    def load(self, filename: str, callback: Optional[Callable[[float], None]] = None) -> None:
        """
        Load an EPUB file into the TTS_Project.

        :param filename: The filename of the EPUB file.
        :type filename: str

        :param callback: The callback function for progress updates.
        :type callback: Optional[Callable[[float], None]]

        :return: None
        """
        book = epub.read_epub(filename)

        epub_items = list(book.get_items_of_type(ITEM_DOCUMENT))

        exclude_ids: list[str]

        source_dir = Path(__file__).resolve().parent.parent

        with open(os.path.join(source_dir, 'data', 'exclude_ids.json'), 'r') as f:
            exclude_ids = json.load(f)

        exclude_ids_str = ", ".join([f'EPUB item ID: "{exclude_id}"' for exclude_id in exclude_ids])
        print(f'Ignoring {exclude_ids_str}')

        for i, epub_item in enumerate(epub_items):
            if epub_item.id not in exclude_ids:
                soup = BeautifulSoup(epub_item.get_body_content(), 'lxml')

                if isinstance(soup, PageElement):
                    self.html_converter.add_from_html(str(soup))

                    # If no chapter titel is found, use the first item
                    chapter_title = self.get_chapter_title(book.toc, epub_item.file_name)

                    # TODO: Do this later
                    # if not chapter_title:
                    #     if len(self.html_converter.get_project().tts_chapters[-1].tts_items) > 0:
                    #         chapter_title = self._smart_truncate(self.html_converter.get_project().tts_chapters[-1].tts_items[0].text).strip()

                    self.html_converter.get_project().tts_chapters[-1].title = chapter_title
            if callback is not None:
                callback(100/len(epub_items) * i)

        self.project = self.html_converter.get_project()
        self.project.clean_empty_chapters()

        title = book.get_metadata('DC', 'title')[0][0]
        author = book.get_metadata('DC', 'creator')[0][0]
        date_metadata = book.get_metadata('DC', 'date')

        date_str = ''

        if len(date_metadata) > 0:
            date_str = book.get_metadata('DC', 'date')[0][0]
        else:
            date_metadata = book.get_metadata('OPF', None)

            if len(date_metadata) > 0:
                date_str = date_metadata[0][0]

        date = parse(date_str, default=datetime.datetime(1, 1, 1))

        for epub_item in book.get_items():
            if epub_item.media_type.startswith('image/'):
                if epub_item.content:
                    self.project.image_bytes = base64.b64encode(epub_item.content)
                    break

        self.project.author = author
        self.project.title = title
        self.project.date = date

    def load_raw(self, content: str, author: str = '', title: str = '', callback: Optional[Callable[[float], None]] = None) -> None:
        """
        Load HTML content into the TTS_Project.

        :param content: The raw HTML content.
        :type content: str

        :param author: Author of the resulting project, defaults to ''
        :type author: str, optional

        :param title: Title of the resulting project, defaults to ''
        :type title: str, optional

        :param callback: The callback function for progress updates.
        :type callback: Optional[Callable[[float], None]]

        :return: None
        """
        return super().load_raw(content, author, title, callback)
