import re
from typing import List, Optional
from num2words import num2words

from tts_arranger.items.element_optimizer import ElementOptimizer
from tts_arranger.items.tts_item import TTS_Item  # type: ignore


class TTS_Preprocessor:
    inline_elements = ["span", "a", "b", "i", "u", "strong", "em", "sub", "sup", "mark"]

    def __init__(self) -> None:
        pass

    def preprocess(self, tts_items: List[TTS_Item], replace: dict) -> List[TTS_Item]:
        words_to_keep_upper = [
            "NASA",
            "FBI",
            "CIA",
            "IBM",
            "BBC",
            "CNN",
            "USA",
            "I",
            "RPG",
            "CRPG",
            "JRPG",
            "CPU",
        ]

        # Optimize item elements first
        optimizer = ElementOptimizer()

        for item in tts_items:
            for element in item.elements:
                if element.text:
                    # element.text = self._cleanup_numbers(element.text)
                    # element.text = self._apply_basic_replacements(element.text, replace)

                    # Remove whitespace before punctuation
                    element.text = re.sub(r"\s+([.,!?])", r"\1", element.text)

                    # Make sure each item ends with space, if not an inline element
                    if element.custom_data:
                        tag = element.custom_data.get("tag", "")
                        if tag:
                            if tag[0] not in self.inline_elements:
                                element.text = element.text.strip() + " "

                    # replace single quote quotation marks with double quote, if beginning and end are found
                    element.text = re.sub(
                        r"(?<!\w)‘(.*?)’(?!\w)", r"“\1”", element.text
                    )

                    # Replace hyphen surrounded by text with space
                    element.text = re.sub(r"(\S)-(\S)", r"\1 \2", element.text)

                    # Find numbers followed by "Hz" or "dB" without a space and add a space
                    element.text = re.sub(r"(\d)([Hd])([dB])", r"\1 \2\3", element.text)

                    # Convert occurrences of "Hz" into "Hertz", check for word boundaries
                    element.text = re.sub(r"\bHz\b", "Hertz", element.text)

                    # Find full stops followed by a space not followed by a capital letter and replace the respective lowercase letter with uppercase
                    element.text = re.sub(
                        r"\. ([a-z])", lambda x: f". {x.group(1).upper()}", element.text
                    )

                    # Find substrings that only contain uppercase letter words with more than one letter and replace them with lowercase, ignore whitespace
                    # element.text = re.sub(
                    #     r"\b[A-Z]{2,}\b(?:\s+\b[A-Z]{2,}\b)*",
                    #     lambda x: " ".join(
                    #         word if word in words_to_keep_upper else word.lower()
                    #         for word in re.findall(r"\b[A-Z]{2,}\b", x.group())
                    #     ),
                    #     element.text,
                    # )

        for tts_item in tts_items:
            tts_item.elements = optimizer.optimize(
                tts_item.elements, max_pause_duration=1500
            )

        return tts_items

    def _apply_basic_replacements(self, text: str, replace: dict) -> str:
        # Remove Japanese characters etc.
        text = "".join(filter(lambda character: ord(character) < 0x3000, text))

        # Replace problematic characters, abbreviations etc
        for k, v in replace.items():
            text = re.sub(k, v, text)

        simple_replacements = [
            ("\u2026", "..."),
            ("\u2013", " - "),
            ("\u00a0", " "),
            (" - ", " — "),
            ("–", " — "),
            (";", ". "),
            (": ", ". "),
            (":", ". "),
            ("(", "\n\n"),
            (")", "\n\n"),
            ("[", "\n\n"),
            ("]", "\n\n"),
            ("…?", "?"),
            ("…!", "!"),
            ("…", "."),
            ("!", "."),
            ("\r", "\n"),
        ]

        special_replacements = [
            ("/", "slash"),
            ("\\", "backslash"),
            ("<", "less than"),
            (">", "greater than"),
            ("=", "equals"),
            ("≠", "not equals"),
            ("≈", "approximately"),
            ("≤", "less than or equal to"),
            ("≥", "greater than or equal to"),
            ("±", "plus minus"),
            ("×", "times"),
            ("÷", "divided by"),
            ("∞", "infinity"),
            ("√", "square root"),
            ("∛", "cube root"),
            ("∜", "fourth root"),
            ("∑", "sum"),
            ("∏", "product"),
            ("∫", "integral"),
            ("∂", "partial"),
            ("∆", "delta"),
            ("$", "dollar"),
            ("€", "euro"),
            ("£", "pound"),
            ("¥", "yen"),
            ("¢", "cent"),
            ("°C", "degrees Celsius"),
            ("°", "degrees"),
            ("℃", "degrees Celsius"),
        ]

        # Apply simple replacements
        for old, new in simple_replacements:
            text = text.replace(old, new)

        # Apply special replacements
        for old, new in special_replacements:
            text = text.replace(old, " " + new + " ")

        return text

    def _cleanup_numbers(self, text: str) -> str:
        # Remove commas in numbers, when used as thousands separator, make sure the all parts after the first are three digits long
        while re.search(r"(\d),(\d{3})", text):
            text = re.sub(r"(\d),(\d{3})", r"\1\2", text)

        # Replace ordinal numbers with words
        text = re.sub(
            r"\b(\d+)(st|nd|rd|th)\b",
            lambda x: num2words(x.group(1), to="ordinal"),
            text,
        )

        # Find and replace year numbers when preceded by month names or "in" with words
        text = re.sub(
            r"\b(January|February|March|April|May|June|July|August|September|October|November|December|in) (\d{1,2}, )?(\d{4})\b",
            lambda x: f"{x.group(1)} {x.group(2) or ''}{num2words(x.group(3), to='year')}",
            text,
        )

        # Replace numbers with words, including decimal numbers
        text = re.sub(r"\b\d+(\.\d+)?\b", lambda x: num2words(x.group()), text)

        return text

    def optimize(self, tts_items: list[dict], max_pause_duration=0) -> list[dict]:
        """
        Merge similar items for smoother synthesizing and avoiding unwanted pauses

        :param max_pause_duration: Maximum duration auf merged pauses
        :type max_pause_duration: int

        :return: None
        """

        final_items: list[dict] = self._merge_items(tts_items)

        non_empty_items: list[dict] = []

        # Remove remaining empty items
        for final_item in final_items:
            stripped_text = final_item.get("text", "").strip()
            if (
                stripped_text
                or final_item.get("min_length", 0) > 0
                or final_item.get("sound_file")
            ):
                non_empty_items.append(final_item)

        # Merge one final time for remaining pauses
        non_empty_items = self._merge_items(non_empty_items)

        # Limit pause duration for pause items, ignore if max_pause_duration == 0
        for non_empty_item in non_empty_items:
            if non_empty_item.get("speaker_id") == -1 and max_pause_duration > 0:
                if non_empty_item.get("min_length", 0) > max_pause_duration:
                    non_empty_item["min_length"] = max_pause_duration

        return non_empty_items

    def _merge_items(self, tts_items: list[dict]) -> list[dict]:
        final_items: list[dict] = []
        merged_item: Optional[dict] = None

        for tts_item in tts_items:
            if not merged_item:
                # Scanning not started
                merged_item = tts_item
            elif merged_item.get("speaker_id", "") == tts_item.get("speaker_id", ""):
                # Starting item and current are similar, add to merge item text and length
                merged_item = {
                    "text": f'{merged_item.get("text", "")} {tts_item.get("text", "")}',
                    "speaker_id": merged_item.get("speaker_id", ""),
                    "min_length": merged_item.get("min_length", 0)
                    + tts_item.get("min_length", 0),
                }
            else:
                # Starting item and current are not similar, add last and current item, set this item as new starting item
                final_items.append(merged_item)
                merged_item = tts_item

        if merged_item is not None:
            final_items.append(merged_item)

        return final_items
