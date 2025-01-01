import re
from typing import Optional


class TTS_Preprocessor:
    def preprocess(self, tts_items: list[dict], replace: dict) -> list[dict]:
        # final_items: list[dict] = []

        for item in tts_items:
            if item.get("text"):

                # Remove Japanese characters etc.
                item["text"] = "".join(
                    filter(lambda character: ord(character) < 0x3000, item["text"])
                )

                # Miscellanous replacements
                # item["text"] = item["text"].replace("…", "\n\n")

                # Replace problematic characters, abbreviations etc
                for k, v in replace.items():
                    item["text"] = re.sub(k, v, item["text"])

                # Make sure each item ends with space
                item["text"] = item["text"].strip() + " "

                # Replace hyphen variants with standard hyphen
                item["text"] = item["text"].replace(" - ", " — ")
                item["text"] = item["text"].replace("–", " — ")
                item["text"] = item["text"].replace(";", ".")
                item["text"] = item["text"].replace(": ", ".")
                item["text"] = item["text"].replace(":", ".")

                # item["text"] = item["text"].replace(" —", ".")

                # replace single quote quotation marks with double quote, if beginning and end are found
                item["text"] = re.sub(r"(?<!\w)‘(.*?)’(?!\w)", r"“\1”", item["text"])

                # Replace hyphen surrounded by text with space
                item["text"] = re.sub(r"(\S)-(\S)", r"\1 \2", item["text"])

                # Replace standard hyphen with two line breaks
                # item["text"] = item["text"].replace(" - ", "\n\n")

                # Find numbers follewed by "Hz" or "dB" without a space and add a space
                item["text"] = re.sub(r"(\d)([Hd])([dB])", r"\1 \2\3", item["text"])

                # Convert occurrences of "Hz" into "Hertz", check for word boundaries
                item["text"] = re.sub(r"\bHz\b", "Hertz", item["text"])

                # Same with brackets
                item["text"] = item["text"].replace("(", "\n\n")
                item["text"] = item["text"].replace(")", "\n\n")

                item["text"] = item["text"].replace("[", "\n\n")
                item["text"] = item["text"].replace("]", "\n\n")

                item["text"] = item["text"].replace("…?", "?")
                item["text"] = item["text"].replace("…!", "!")
                item["text"] = item["text"].replace("….", ".")

                # Replace ellipsis with full stop
                item["text"] = item["text"].replace("…", ".")

                # TODO: Temporary fix
                item["text"] = item["text"].replace("!", ".")

                # Replace \r with \n
                item["text"] = item["text"].replace("\r", "\n")

                # Find full stops followed by a space not followed by a capital letter and replace the respective lowercase letter with uppercase
                item["text"] = re.sub(
                    r"\. ([a-z])", lambda x: f". {x.group(1).upper()}", item["text"]
                )

                # Find all words with more than 3 characters only containing uppercase letters and replace them with lowercase
                item["text"] = re.sub(
                    r"\b[A-Z]{3,}\b", lambda x: x.group().lower(), item["text"]
                )

                # Make sure sentences end with a period if not already ending with a punctuation mark, question mark, exclamation mark, etc.
                # if not item["text"].endswith((".", "!", "?", "…", ":")):
                #     item["text"] = item["text"].strip() + "."

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
                # if stripped_text:
                #     final_item["text"] = stripped_text
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
