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
    Class for converting HTML to a TTS_Project or list of TTS_Item objects. Works on an internal project object that can be retrieved after loading all needed data is finished.
    """
    project: TTS_Project

    def __init__(self, *, convert_charrefs: bool = True, default_properties=CheckerItemProperties(pause_after=250), custom_checkers: Optional[list[Checker]] = None, custom_checkers_files: Optional[list[str]] = None, ignore_default_checkers: bool = False) -> None:
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

        self.default_properties = default_properties
        self.last_signal = CHECKER_SIGNAL.NO_SIGNAL

        # Initialize list with custom checkers so they have the highest priority
        self.checkers: list[Checker] = custom_checkers or []

        if custom_checkers:
            print(f'{len(custom_checkers)} custom checker entries added.')

        self.checker_results_stack: list[tuple[CHECK_SPEAKER_RESULT, CHECKER_SIGNAL, Optional[CheckerItemProperties]]] = []

        # Add checkers from custom files
        if custom_checkers_files:
            for custom_checkers_file in custom_checkers_files:
                self.add_checkers_from_json(custom_checkers_file)

        # Finally add default checkers from data folder (lowest priority)
        if not ignore_default_checkers:
            source_dir = Path(__file__).resolve().parent.parent
            base_path = os.path.dirname(__file__) if __file__ else str(source_dir)
            default_file = os.path.join(base_path, 'data', 'checkers_default.json')

            self.add_checkers_from_json(default_file)

        # Push default starting properties to stack
        self.checker_results_stack.append((CHECK_SPEAKER_RESULT.NOT_MATCHED, CHECKER_SIGNAL.NO_SIGNAL, default_properties))

        self.project = TTS_Project()
        self.current_item: Optional[TTS_Item] = None

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
        # Ignore script, style tags, etc.
        if name in ['script', 'style', 'meta']:
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

    def add_checkers_from_json(self, filename: str = '') -> None:
        """
        Load and add checkers from a checkers JSON file.

        :param filename: Filename of the checkers file to load (in JSON format), defaults to ''
        :type filename: str, optional

        :return: None
        """

        json_check_entries = []

        if not os.path.exists(filename):
            print(f'Checkers file "{filename}" does not exist, skipping.')
            return

        print(f'Loading checkers file "{filename}".')

        with open(filename, 'r') as file:
            data = json.load(file)

            json_check_entries = data['check_entries']

        for json_entry in json_check_entries:

            # Access the conditions list for the entry
            json_conditions = json_entry['conditions']

            conditions: list[Condition] = []

            for json_condition in json_conditions:
                # Access the name and arg properties of the condition
                name = json_condition['name']
                arg = json_condition['arg']

                condition: Optional[Condition] = None

                match name:
                    case 'Name':
                        condition = ConditionName(arg)
                    case 'Class':
                        condition = ConditionClass(arg)
                    case 'ID':
                        condition = ConditionID(arg)
                    case _:
                        print(f'Unknown checker condition found: {name}')

                if condition:
                    if condition.arg:
                        conditions.append(condition)

            # Access properties dictionary for entry
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

            # Access signals list for entry
            if 'signal' in json_entry:
                json_signal = json_entry['signal']

                match json_signal:
                    case 'NEW_CHAPTER':
                        signal = CHECKER_SIGNAL.NEW_CHAPTER
                    case 'IGNORE':
                        signal = CHECKER_SIGNAL.IGNORE
                    case _:
                        print(f'Unknown checker signal found: {json_signal}')

            self.checkers.append(Checker(conditions, properties, signal))
        print(f'{len(json_check_entries)} checkers entries added.')

    def get_project(self) -> TTS_Project:
        """
        Returns the finished TTS project.
        """
        return self.project
