import base64
import datetime
import pickle
from dataclasses import dataclass, field


import requests  # type: ignore

from ..utils.log import LOG_TYPE, log
from .tts_chapter import TTS_Chapter  # type: ignore
from .tts_item import TTS_Item  # type: ignore


@dataclass
class TTS_Project():
    """
    A data class representing a text-to-speech project.

    :param tts_chapters: A list of TTS chapter representing the chapters of the project. Default value is an empty list.
    :type tts_chapters: list[TTS_Chapter]

    :param title: A string representing the title of the project. Default value is an empty string.
    :type title: str

    :param subtitle: A string representing the subtitle of the project. Default value is an empty string.
    :type subtitle: str

    :param date: A datetime.datetime object representing the date of the project. Default value is datetime.datetime.min.
    :type date: datetime.datetime

    :param author: A string representing the author of the project. Default value is an empty string.
    :type author: str

    :param lang_code: A string representing the language code of the project. Default value is 'en'.
    :type lang_code: str

    :param image_bytes: A bytes object representing the image of the project encoded as b64. Default value is an empty bytes object.
    :type image_bytes: bytes

    :param raw: Defines if this should be synthesized without optimization and preprocessing.
    :type raw: boolean
    """

    tts_chapters: list[TTS_Chapter] = field(default_factory=list)

    title: str = ''
    subtitle: str = ''
    date: datetime.datetime = datetime.datetime.min
    author: str = ''
    lang_code: str = 'en'
    image_bytes: bytes = bytes(0)

    raw: bool = False

    @classmethod
    def from_json_file(cls, filename: str = ''):
        """
        Class method to load a TTS project from a JSON file.

        :param filename: A string representing the name of the JSON file to be loaded. Default value is an empty string.
        :type filename: str

        :return: A TTS project object loaded from the JSON file.
        :rtype: TTS_Project
        """
        if filename:
            try:
                with open(filename, 'rb') as file:
                    return pickle.load(file)
            except IOError:
                log(LOG_TYPE.WARNING, f'TTS Project export file "{filename}" could not be opened for reading.')
        return TTS_Project()

    @classmethod
    def from_items(cls, tts_items: list[TTS_Item]):
        """
        Convenience method to create a TTS project from a list of TTS items.

        :param filename: A list with TTS item to create TTS project from (containing a single chapter containing the items).
        :type filename: str

        :return: A TTS project object loaded from the JSON file.
        :rtype: TTS_Project
        """
        return TTS_Project([TTS_Chapter(tts_items)])

    def merge_from_project(self, project) -> None:
        """
        Merges the contents of another TTS project into this one.

        :param project: The TTS project to be merged.
        :type project: TTS_Project

        :return: None
        :rtype: None
        """
        if isinstance(project, TTS_Project):
            self.tts_chapters += project.tts_chapters

    def append(self, items: list[TTS_Item]) -> None:
        """
        Adds a list of TTS items to the last TTS chapter of this TTS project.

        :param items: A list of TTS items to be added to the last chapter.
        :type items: list[TTS_Item]

        :return: None
        :rtype: None
        """

        if not self.tts_chapters:
            self.tts_chapters.append(TTS_Chapter())

        self.tts_chapters[-1].tts_items += items

    def to_json_file(self, filename: str) -> None:
        """
        Saves the TTS project to a JSON file.

        :param filename: A string representing the name of the JSON file to be saved.
        :type filename: str

        :return: None
        :rtype: None
        """
        try:
            with open(filename, 'wb') as file:
                pickle.dump(self, file)
        except IOError:
            log(LOG_TYPE.WARNING, f'TTS Project export file "{filename}" could not be opened for writing.')

    def add_image_from_url(self, image_url: str) -> None:
        """
        Loads the image from the given URL and sets it as the project image.

        :param image_url: The URL of the image to be added.
        :type image_url: str

        :return: None
        """
        if image_url:
            self.image_bytes = base64.b64encode(requests.get(image_url).content)

    def clean_empty_chapters(self):       
        """
        Remove empty chapters.
        """         
        final_chapters: list[TTS_Chapter] = []

        for chapter in self.tts_chapters:
            if len(chapter.tts_items) > 0:
                final_chapters.append(chapter)

        self.tts_chapters = final_chapters

    def optimize(self, max_pause_duration=0) -> None:
        """
        Merge similar items for smoother synthesizing and avoiding unwanted pauses

        :param max_pause_duration: Maximum duration auf merged pauses
        :type max_pause_duration: int

        :return: None
        """

        for chapter in self.tts_chapters:
            chapter.optimize(max_pause_duration)

    def get_titles(self, only_empty=True, max_length=100) -> None:
        """
        Set chapter titles to the text of the first chapter's item

        :param only_empty: Only set empty titles
        :type only_empty: bool

        :param max_length: Maximus title length, a '…' will be added after this
        :type max_length: int

        :return: None
        """
        for chapter in self.tts_chapters:
            chapter.get_title(only_empty, max_length)
