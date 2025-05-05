import base64
import datetime
import json
import pickle
from dataclasses import asdict, dataclass, field
from typing import List, Optional

import requests  # type: ignore
from dateutil import parser # type: ignore
from loguru import logger

from tts_arranger.items.tts_chapter import TTS_Chapter  # type: ignore
from tts_arranger.items.tts_element import TTS_Element
from tts_arranger.items.tts_item import TTS_Item  # type: ignore


@dataclass
class TTS_Project:
    chapters: List[TTS_Chapter] = field(default_factory=list)

    title: str = ""
    subtitle: str = ""
    date: datetime.datetime = datetime.datetime.min
    author: str = ""
    lang_code: str = "en"
    image_bytes: bytes = bytes(0)

    raw: bool = False

    @classmethod
    def from_json_file(cls, filename: str = "") -> "TTS_Project":
        if filename:
            try:
                with open(filename, "r", encoding="utf-8") as file:
                    json_data = file.read()
                    return cls.from_json(json_data)
            except IOError as e:
                logger.error(f"Error reading file {filename}: {e}")
                raise
        return TTS_Project()

    @classmethod
    def from_json(cls, json_str: str) -> "TTS_Project":
        try:
            data = json.loads(json_str)
            return cls(
                chapters=[
                    TTS_Chapter.from_json(chapter)
                    for chapter in data.get("chapters", [])
                ],
                title=data.get("title", ""),
                subtitle=data.get("subtitle", ""),
                date=parser.parse(data.get("date", datetime.datetime.min.isoformat())),
                author=data.get("author", ""),
                lang_code=data.get("lang_code", "en"),
                image_bytes=base64.b64decode(data.get("image_bytes", "")),
                raw=data.get("raw", False),
            )
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.error(f"Failed to parse JSON data: {e}")
            raise

    def to_json(self) -> str:
        try:
            data = asdict(self)
            data["date"] = self.date.isoformat()
            data["image_bytes"] = base64.b64encode(self.image_bytes).decode("utf-8")
            data["chapters"] = [chapter.to_json() for chapter in self.chapters]
            return json.dumps(data)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to convert to JSON: {e}")
            raise

    @classmethod
    def from_items(cls, tts_items: List[TTS_Item]) -> "TTS_Project":
        return TTS_Project([TTS_Chapter(tts_items)])

    def merge_from_project(self, project: "TTS_Project") -> None:
        if isinstance(project, TTS_Project):
            self.chapters += project.chapters

    def dump_as_json_file(self, filename: str) -> None:
        try:
            with open(filename, "wb") as file:
                pickle.dump(self, file)
        except IOError:
            logger.warning(
                f'TTS Project export file "{filename}" could not be opened for writing.'
            )

    def add_image_from_url(self, image_url: str) -> None:
        if image_url:
            # Identify as browser to avoid problems with servers like wikimedia
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
            }
            self.image_bytes = base64.b64encode(
                requests.get(image_url, headers=headers).content
            )

    def add_image_from_file(self, image_path: str) -> None:
        try:
            with open(image_path, "rb") as file:
                self.image_bytes = base64.b64encode(file.read())
        except IOError:
            logger.warning(
                f'TTS Project image file "{image_path}" could not be opened for reading.'
            )

    def _check_empty_chapter(self, chapter: TTS_Chapter) -> bool:
        for item in chapter.items:
            for element in item.elements:
                if element.text.strip() != "":
                    return False
        return True

    def clean_empty_chapters(self) -> None:
        final_chapters: List[TTS_Chapter] = []

        # for chapter in self.chapters:
        #     if len(chapter.items) > 0:
        #         final_chapters.append(chapter)

        # Remove empty chapters
        for chapter in self.chapters:
            final_items = []
            for item in chapter.items:
                for element in item.elements:
                    if element.text.strip() != "" or (
                        element.speaker_id == "" and element.min_length > 0
                    ):
                        final_items.append(item)
                        break

            # Check if remaining items are all pauses
            if len(final_items) > 1:
                if not self._check_empty_chapter(TTS_Chapter(final_items)):
                    final_chapters.append(chapter)

        self.chapters = final_chapters

    # def optimize(self, max_pause_duration: int = 0) -> None:
    #     for chapter in self.chapters:
    #         chapter.optimize(max_pause_duration)

    def set_titles(self, only_empty: bool = True, max_length: int = 100) -> None:
        for chapter in self.chapters:
            chapter.set_title(only_empty, max_length)

    def get_titles(self) -> None:
        pass

    def get_output_filename(self) -> str:
        return self.author + " - " + self.title

    def add_element(
        self,
        element: TTS_Element,
        chapter_index: Optional[int] = None,
        item_index: Optional[int] = None,
    ) -> None:
        """
        Add a TTS_Element to the project at the specified chapter and item index.

        :param element: The TTS_Element to add.
        :param chapter_index: The index of the chapter to add the element to. If None, add to the last chapter.
        :param item_index: The index of the item to add the element to. If None, add to the last item.
        """

        if chapter_index is None:
            chapter_index = -1

        if item_index is None:
            item_index = -1

        if chapter_index >= len(self.chapters) or len(self.chapters) == 0:
            self.chapters.append(TTS_Chapter())

        if (
            item_index >= len(self.chapters[chapter_index].items)
            or len(self.chapters[chapter_index].items) == 0
        ):
            self.chapters[chapter_index].items.append(TTS_Item())

        self.chapters[chapter_index].items[item_index].elements.append(element)

    def add_item(
        self,
        item: TTS_Item,
        chapter_index: Optional[int] = None,
        item_index: Optional[int] = None,
    ) -> None:
        """
        Add a TTS_Item to the project at the specified chapter and item index.

        :param item: The TTS_Item to add.
        :param chapter_index: The index of the chapter to add the item to. If None, add to the last chapter.
        :param item_index: The index of the item to add the item to. If None, add to the last item.
        """

        if chapter_index is None:
            chapter_index = -1

        if item_index is None:
            item_index = -1

        if chapter_index >= len(self.chapters) or len(self.chapters) == 0:
            self.chapters.append(TTS_Chapter())

        self.chapters[chapter_index].items.append(item)

    def __str__(self) -> str:
        return " ".join([chapter.title for chapter in self.chapters])

    def __len__(self) -> int:
        return len(self.chapters)

    def __getitem__(self, key: int) -> TTS_Chapter:
        return self.chapters[key]

    def __setitem__(self, key: int, value: TTS_Chapter) -> None:
        self.chapters[key] = value

    def __delitem__(self, key: int) -> None:
        del self.chapters[key]

    def insert(self, index: int, value: TTS_Chapter) -> None:
        self.chapters.insert(index, value)

    def append(self, value: TTS_Chapter) -> None:
        self.chapters.append(value)

    def extend(self, values: List[TTS_Chapter]) -> None:
        self.chapters.extend(values)

    def remove(self, value: TTS_Chapter) -> None:
        self.chapters.remove(value)

    def pop(self, index: int = -1) -> TTS_Chapter:
        return self.chapters.pop(index)

    def clear(self) -> None:
        self.chapters.clear()

    def copy(self) -> "TTS_Project":
        return TTS_Project(
            chapters=self.chapters.copy(),
            title=self.title,
            subtitle=self.subtitle,
            date=self.date,
            author=self.author,
            lang_code=self.lang_code,
            image_bytes=self.image_bytes,
            raw=self.raw,
        )
