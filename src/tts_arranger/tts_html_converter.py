import copy
import json
import os
from enum import Enum, auto
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

from tts_arranger.items.tts_item import TTS_Item  # type: ignore
from tts_arranger.tts_writer import TTS_Chapter, TTS_Project  # type: ignore

from tts_arranger.tts_reader.checker import (CHECK_SPEAKER_RESULT, CHECKER_SIGNAL, Checker,
                     CheckerItemProperties, Condition, ConditionClass,
                     ConditionID, ConditionName, Element)


class CONVERSION_MODE(Enum):
    ITEMS = auto()
    PROJECT = auto()


class TTS_HTML_Converter(HTMLParser):
    """
    Class for converting HTML to a TTS_Project or list of TTS_Item objects.
    """
    project: TTS_Project

    def __init__(self, *, convert_charrefs: bool = True, checkers: Optional[list[Checker]] = None, default_properties=CheckerItemProperties(pause_after=250)) -> None:
        """
        Initializes a TTS_HTML_Converter object.

        :param convert_charrefs: A boolean indicating whether to replace HTML character references with their corresponding Unicode characters.
        :type convert_charrefs: bool

        :param checkers: An optional list of Checker objects to use for checking each HTML element.
        :type checkers: Optional[list[Checker]]

        :param default_properties: An optional CheckerItemProperties object that represents the default properties for all HTML elements.
        :type default_properties: CheckerItemProperties
        """
        super().__init__(convert_charrefs=convert_charrefs)

        self.checkers: list[Checker] = checkers or []

        self.default_properties = default_properties

        self.last_signal = CHECKER_SIGNAL.NO_SIGNAL

        self.checker_results_stack: list[tuple[CHECK_SPEAKER_RESULT, CHECKER_SIGNAL, Optional[CheckerItemProperties]]] = []

        # Push default properties to stack to start with
        self.checker_results_stack.append((CHECK_SPEAKER_RESULT.NOT_MATCHED, CHECKER_SIGNAL.NO_SIGNAL, default_properties))

        self.project = TTS_Project()
        self.current_item: TTS_Item | None = None

    def tag_to_element(self, name: str, attrs: list) -> Element:
        """
        Converts an HTML tag to an Element object.

        :param name: The name of the HTML tag.
        :type name: str
        
        :param attrs: The attributes of the HTML tag.
        :type attrs: list
        
        :return: An Element object representing the HTML tag.
        """
        elem = Element(name)

        for attr in attrs:
            match attr[0]:
                case 'id':
                    elem.id = attr[1]
                case 'class':
                    elem.classes = attr[1].split()
        return elem

    def handle_starttag(self, name: str, attrs: list) -> None:
        """
        Handles the start of an HTML tag.

        :param name: The name of the HTML tag.
        :type name: str
        
        :param attrs: The attributes of the HTML tag.
        :type attrs: list
        """
        # Ignore scripts
        if name == 'script':
            result = CHECK_SPEAKER_RESULT.MATCHED
            signal = CHECKER_SIGNAL.IGNORE
            properties = None
        else:
            result, signal, properties = copy.deepcopy(self._check_elem(self.tag_to_element(name, attrs), self.checkers))

            if result != CHECK_SPEAKER_RESULT.MATCHED:
                # If there are no specific properties for this tag, continue to use parent tag's speaker properties (but no pause)
                _, signal, properties = copy.deepcopy(self.checker_results_stack[-1])

                if properties:
                    properties.pause_after = self.default_properties.pause_after
                    result = CHECK_SPEAKER_RESULT.NOT_MATCHED

        if properties:
            # Only apply speaker index if its above the parent tag (for nested tags)
            _, _, parent_properties = copy.deepcopy(self.checker_results_stack[-1])

            if parent_properties:
                if properties.speaker_idx < parent_properties.speaker_idx:
                    properties.speaker_idx = parent_properties.speaker_idx

        self.checker_results_stack.append((result, signal, properties))

    def handle_data(self, data: str) -> None:
        """
        Handles the data between two HTML tags.

        :param data: The data between two HTML tags.
        :type data: str.
        """
        (_, signal, properties) = self.checker_results_stack[-1]

        match signal:
            case CHECKER_SIGNAL.IGNORE:
                return
            case CHECKER_SIGNAL.NEW_CHAPTER:
                # Prepare a new chapter
                self.current_chapter = TTS_Chapter()
                self.project.tts_chapters.append(self.current_chapter)

        if properties:
            self.current_item = TTS_Item(data, properties.speaker_idx)
            self.current_chapter.tts_items.append(self.current_item)

    def handle_endtag(self, name: str) -> None:
        """
        Handles the end of an HTML tag.

        :param name: The name of the HTML tag.
        :type name: str
        """
        (result, signal, properties) = self.checker_results_stack.pop()

        add_pause = False

        # Don't create pauses for ignored segments
        if signal == CHECKER_SIGNAL.IGNORE:
            return

        # Create pause if this tag has a special settings, otherwise use
        if result == CHECK_SPEAKER_RESULT.MATCHED:
            add_pause = True
        else:
            # Don't create pauses after inline segments
            if name in ['span', 'i', 'b', 'u', 'a', 'em']:
                return

        # Only create pauses after valid segments
        # if self.current_item and not self.current_item.text.strip():
        #     return

        if add_pause:
            if self.current_chapter:
                if properties:
                    if properties.pause_after > 0:
                        self.current_chapter.tts_items.append(TTS_Item(length=properties.pause_after))
        self.current_item = None

    def _check_elem(self, elem: Element, checkers: list[Checker]) -> tuple[CHECK_SPEAKER_RESULT, CHECKER_SIGNAL, Optional[CheckerItemProperties]]:
        """
        Checks an HTML element against a list of Checkers.

        :param elem: An Element object representing the HTML element to check.
        :type elem: Element

        :param checkers: A list of Checker objects to use for checking the HTML element.
        :type checkers: checkers: list[Checker]

        :return: A tuple of the CHECK_SPEAKER_RESULT, CHECKER_SIGNAL, and CheckerItemProperties objects representing the result of the check.
        """
        for checker in checkers:
            result, signal, properties = checker.determine(elem)

            if result != CHECK_SPEAKER_RESULT.NOT_MATCHED:
                return result, signal, properties
        return CHECK_SPEAKER_RESULT.NOT_MATCHED, CHECKER_SIGNAL.NO_SIGNAL, None

    def add_from_html(self, html: str, new_chapter=True) -> None:
        """
        Converts from HTML and adds to the existing TTS_Project object in the buffer.

        :param html: The HTML string to convert.
        :type html: str

        :param new_chapter: A boolean indicating whether to start a new chapter.
        :type new_chapter: bool

        :return: None
        """
        if new_chapter:
            self.current_chapter = TTS_Chapter()
            self.project.tts_chapters.append(self.current_chapter)

        self.feed(html)

        # Remove empty items
        for chapter in self.project.tts_chapters:
            final_items = []
            for item in chapter.tts_items:
                if item.text != '' or (item.speaker_idx == -1 and item.length > 0):
                    final_items.append(item)

            chapter.tts_items = final_items

    def convert_from_html(self, html: str, conversion_mode: CONVERSION_MODE = CONVERSION_MODE.PROJECT) -> Optional[TTS_Project | list[TTS_Item]]:
        """
        Converts from HTML and returns a TTS_Project object or a list of TTS_Item objects.

        :param html: The HTML string to convert.
        :type html: str

        :param conversion_mode: The mode of conversion.
        :type conversion_mode: CONVERSION_MODE

        :return: A TTS_Project object or a list of TTS_Item objects.
        """
        self.project = TTS_Project()

        self.add_from_html(html)

        match conversion_mode:
            case CONVERSION_MODE.PROJECT:
                return self.project
            case CONVERSION_MODE.ITEMS:
                if self.project.tts_chapters:
                    return self.project.tts_chapters[-1].tts_items

        return None

    def get_checkers_files(self, filename: str = '', default_filename: str = '', ignore_default: bool = False) -> list[str]:
        """
        Compiles a list of checkers files, sorted by priority, starting with the first file (if available), adding the default file (if available), and finally adding the library default file

        :param filename: Filename of the checkers file to load (in JSON format), defaults to ''
        :type filename: str, optional

        :param default_filename: Filename of a fallback checkers file to load, defaults to ''
        :type default_filename: str, optional

        :param ignore_default: Defines if the library's default checkers file should be ignored, defaults to False
        :type ignore_default: bool, optional

        :return: List of checkers
        :rtype: list[str]
        """
        files: list[str] = []

        if os.path.exists(filename):
            files.append(filename)

        # Check for default file in the same path
        if default_filename:
            if os.path.exists(default_filename):
                files.append(default_filename)

        # Check for default file
        if ignore_default:
            return files
        
        source_dir = Path(__file__).resolve().parent.parent

        base_path = os.path.dirname(__file__) if __file__ else str(source_dir)
        default_file = os.path.join(base_path, 'data', 'checkers_default.json')
        if os.path.exists(default_file):
            files.append(default_file)
            return files

        raise FileNotFoundError(f'No checkers file or default file found.')

    def add_checkers_from_json(self, filename: str = '', default_filename: str = '', ignore_default=False) -> None:
        """
        Load and add a list of checkers files.

        :param filename: Filename of the checkers file to load (in JSON format), defaults to ''
        :type filename: str, optional

        :param default_filename: Filename of a fallback checkers file to load, defaults to ''
        :type default_filename: str, optional

        :param ignore_default: Defines if the library's default checkers file should be ignored, defaults to False
        :type ignore_default: bool, optional

        :return: None
        """
        for checker_file in self.get_checkers_files(filename, default_filename, ignore_default):
            print(f'Loading checkers file "{checker_file}"')

            json_check_entries = []

            with open(checker_file, 'r') as file:
                data = json.load(file)

                json_check_entries = data['check_entries']

            print(f'{len(json_check_entries)} checker entries found.')
            for json_entry in json_check_entries:

                # Access the conditions list for the entry
                json_conditions = json_entry['conditions']

                conditions: list[Condition] = []

                for json_condition in json_conditions:
                    # Access the name and arg properties of the condition
                    name = json_condition['name']
                    arg = json_condition['arg']

                    condition: Condition | None = None

                    match name:
                        case 'Name':
                            condition = ConditionName(arg)
                        case 'Class':
                            condition = ConditionClass(arg)
                        case 'ID':
                            condition = ConditionID(arg)
                        case _:
                            pass

                    if condition:
                        if condition.arg:
                            conditions.append(condition)

                # Access the properties dictionary for the entry
                json_properties = json_entry['properties']

                properties: Optional[CheckerItemProperties] = None

                speaker_idx = 0
                pause_after = 0

                if 'speaker_idx' in json_properties:
                    speaker_idx = int(json_properties['speaker_idx'])
                if 'pause_after' in json_properties:
                    pause_after = int(json_properties['pause_after'])

                properties = CheckerItemProperties(speaker_idx, pause_after)

                signal = CHECKER_SIGNAL.NO_SIGNAL

                # Access the signals list for the entry
                if 'signal' in json_entry:
                    json_signal = json_entry['signal']

                    match json_signal:
                        case 'NEW_CHAPTER':
                            signal = CHECKER_SIGNAL.NEW_CHAPTER
                        case 'IGNORE':
                            signal = CHECKER_SIGNAL.IGNORE
                        case _:
                            pass

                self.checkers.append(Checker(conditions, properties, signal))

    def get_project(self) -> TTS_Project:
        """
        Returns the finished TTS project.
        """
        return self.project
