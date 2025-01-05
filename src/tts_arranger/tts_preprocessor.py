import re
from typing import Optional
from num2words import num2words  # type: ignore


class TTS_Preprocessor:
    def preprocess(self, tts_items: list[dict], replace: dict) -> list[dict]:
        simple_replacements = [
            (" - ", " — "),
            ("–", " — "),
            (";", ". "),
            (": ", ". "),
            (":", ". "),
            ("/", " slash "),
            ("\\", " backslash "),
            ("<", " less than "),
            (">", " greater than "),
            ("=", " equals "),
            ("≠", " not equals "),
            ("≈", " approximately "),
            ("≤", " less than or equal to "),
            ("≥", " greater than or equal to "),
            ("±", " plus minus "),
            ("×", " times "),
            ("÷", " divided by "),
            ("∞", " infinity "),
            ("√", " square root "),
            ("∛", " cube root "),
            ("∜", " fourth root "),
            ("∑", " sum "),
            ("∏", " product "),
            ("∫", " integral "),
            ("∂", " partial "),
            ("∆", " delta "),
            ("$", " dollar "),
            ("€", " euro "),
            ("£", " pound "),
            ("¥", " yen "),
            ("¢", " cent "),
            ("°C", " degrees Celsius "),
            ("°", " degrees "),
            ("℃", " degrees Celsius "),
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

        for item in tts_items:
            if item.get("text"):
                # Remove Japanese characters etc.
                item["text"] = "".join(
                    filter(lambda character: ord(character) < 0x3000, item["text"])
                )

                # Replace ordinal numbers with words
                item["text"] = re.sub(
                    r"\b(\d+)(st|nd|rd|th)\b",
                    lambda x: num2words(x.group(1), to="ordinal"),
                    item["text"],
                )

                # Find and replace year numbers when preceded by month names or "in" with words
                item["text"] = re.sub(
                    r"\b(January|February|March|April|May|June|July|August|September|October|November|December|in) (\d{1,2}, )?(\d{4})\b",
                    lambda x: f"{x.group(1)} {x.group(2) or ''}{num2words(x.group(3), to='year')}",
                    item["text"],
                )

                # Replace numbers with words, including decimal numbers
                item["text"] = re.sub(
                    r"\b\d+(\.\d+)?\b", lambda x: num2words(x.group()), item["text"]
                )

                # Replace problematic characters, abbreviations etc
                for k, v in replace.items():
                    item["text"] = re.sub(k, v, item["text"])

                # Apply simple replacements
                for old, new in simple_replacements:
                    item["text"] = item["text"].replace(old, new)

                # Make sure each item ends with space
                item["text"] = item["text"].strip() + " "

                # replace single quote quotation marks with double quote, if beginning and end are found
                item["text"] = re.sub(r"(?<!\w)‘(.*?)’(?!\w)", r"“\1”", item["text"])

                # Replace hyphen surrounded by text with space
                item["text"] = re.sub(r"(\S)-(\S)", r"\1 \2", item["text"])

                # Find numbers followed by "Hz" or "dB" without a space and add a space
                item["text"] = re.sub(r"(\d)([Hd])([dB])", r"\1 \2\3", item["text"])

                # Convert occurrences of "Hz" into "Hertz", check for word boundaries
                item["text"] = re.sub(r"\bHz\b", "Hertz", item["text"])

                # Find full stops followed by a space not followed by a capital letter and replace the respective lowercase letter with uppercase
                item["text"] = re.sub(
                    r"\. ([a-z])", lambda x: f". {x.group(1).upper()}", item["text"]
                )

                # Find substrings that only contain uppercase letter words and replace them with lowercase, ignore whitespace
                words_to_keep_upper = [
                    "NASA",
                    "FBI",
                    "CIA",
                    "IBM",
                    "BBC",
                    "CNN",
                    "USA",
                    "I",
                ]
                item["text"] = re.sub(
                    r"\b[A-Z]+\b(?:\s+\b[A-Z]+\b)*",
                    lambda x: " ".join(
                        word if word in words_to_keep_upper else word.lower()
                        for word in re.findall(r"\b[A-Z]+\b", x.group())
                    ),
                    item["text"],
                )

        return tts_items

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
