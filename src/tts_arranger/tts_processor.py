import contextlib
import copy
import csv
import datetime
import os
import re
import string
import sys
import time
from pathlib import Path
from typing import Callable, Optional

import numpy as np  # type: ignore
import TTS  # type: ignore
from num2words import num2words  # type: ignore
from pydub import AudioSegment  # type: ignore
from pydub.silence import detect_silence  # type: ignore
from TTS.utils.manage import ModelManager  # type: ignore
from TTS.utils.synthesizer import Synthesizer  # type: ignore

from .items.tts_item import TTS_Item
from .utils.audio import numpy_to_segment
from .utils.log import LOG_TYPE, bcolors, log


class TTS_Processor:
    def __init__(self, model='', vocoder: str = '', preferred_speakers: Optional[list[str]] = None) -> None:
        """
        Initializes a new instance of the TTS class.

        :param model: Name of the text-to-speech model to use.
        :type model: str

        :param vocoder: Name of the vocoder to use.
        :type vocoder: str

        :param preferred_speakers: A list of preferred speaker names for multi-speaker models to be used instead of the available speakers of the selected model (not yet implemented).
                                If set to None, the default speaker(s) will be used.
        :type preferred_speakers: list[str] or None

        :return: None
        """
        self.model = model or 'tts_models/en/vctk/vits'
        self.vocoder = vocoder
        self.silence_length = 100
        self.silence_threshold = -60
        # self.pause_post_regular =

        # self.quotes = quotes
        self.current_speaker_idx = 0

        self.speakers: list[str] = []

        # Config
        self.pause_sentence = 750
        self.pause_question_exclamation = 1000
        self.pause_parentheses = 300
        self.pause_dash = 300
        self.pause_newline = 250
        self.pause_colon = 100

        self.preferred_speakers = preferred_speakers or []

        # if not self.default_speakers:
        #     with open(os.path.dirname(os.path.realpath(__file__)) + '/speakers', 'r') as speaker_file:
        #         self.default_speakers = speaker_file.read().split()

        # if speakers:
        #     self.default_speakers = speakers

        self.replace = {}

        source_dir = Path(__file__).resolve().parent

        # Load general replace list
        with open(source_dir / 'data/replace', 'r') as file:
            for row in csv.reader(file, delimiter='\t'):
                self.replace[row[0]] = row[1]

        # Load language specific replace list
        lang = self.model.split('/')[1] if '/' in self.model else 'en'

        with open(source_dir / f'data/replace_{lang}', 'r') as file:
            for row in csv.reader(file, delimiter='\t'):
                self.replace[row[0]] = row[1]

    # def __del__(self):
    #     self.temp_dir.cleanup()
    #     self.synthesizer = None
    #     gc.collect()

    def initialize(self) -> None:
        """
        Initializes the text-to-speech (TTS) system, downloads the specified models, and populates the speaker list.

        :return: None
        """
        log(LOG_TYPE.INFO, f'Initializing speech synthesizer')
        models_dir = Path(TTS.__file__).resolve().parent / '.models.json'
        self.manager = ModelManager(str(models_dir))

        with contextlib.redirect_stdout(None):
            (model_path, config_path, _), (vocoder_path, vocoder_config_path, _) = [
                self.manager.download_model(m) if m else ('', '', '') for m in (self.model, self.vocoder)
            ]

            self.synthesizer = Synthesizer(
                tts_checkpoint=model_path,
                tts_config_path=config_path,
                vocoder_checkpoint=vocoder_path,
                vocoder_config=vocoder_config_path if self.vocoder else '',
            )

            # Get speaker list from model
            if self.synthesizer.tts_model and self.synthesizer.tts_model.num_speakers > 1:
                self.speakers = list(self.synthesizer.tts_model.speaker_manager.name_to_id.keys())

    # def _find_and_break(self, tts_items: list[TTS_Item], break_at: list[str], break_after: int) -> list[TTS_Item]:
    #     final_items = []

    #     for tts_item in tts_items:
    #         line = tts_item.text
    #         found = False

    #         if len(line) > break_after:
    #             for b in break_at:
    #                 find = line.rfind(b, 0, break_after)

    #                 if find >= 0:
    #                     final_items.append(TTS_Item(line[:find].strip(), tts_item.speaker, tts_item.pause_pre, tts_item.pause_post, tts_item.strip_silence))
    #                     final_items += self._find_and_break([TTS_Item(line[find + 1:].strip(), tts_item.speaker, tts_item.pause_pre,
    #                                                         tts_item.pause_post, tts_item.strip_silence)], break_at, break_after)
    #                     found = True
    #                     break

    #             if not found:
    #                 # No save spot for breaking found, do a hard break
    #                 final_items.append(TTS_Item(line[:break_after].strip(), tts_item.speaker, tts_item.pause_pre, tts_item.pause_post, tts_item.strip_silence))
    #                 final_items += self._find_and_break([TTS_Item(line[break_after:].strip(), tts_item.speaker, tts_item.pause_pre,
    #                                                     tts_item.pause_post, tts_item.strip_silence)], break_at, break_after)
    #         else:
    #             final_items.append(TTS_Item(line.strip(), tts_item.speaker, tts_item.pause_pre, tts_item.pause_post, tts_item.strip_silence))

    #     return final_items

    def _de_thorsten_tacotron2_DDC_tweaks(self, tts_item: TTS_Item) -> TTS_Item:
        """
        Apply tweaks for tts_models/de/thorsten/tacotron2-DDC.

        :param tts_item: The input TTS item to be processed.
        :type tts_item: TTS_Item

        :return: The processed TTS item with applied tweaks.
        :rtype: TTS_Item
        """
        str_months = ('Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember')

        # Ordinal numbers
        def replace_number(match):
            num = match.group(0)
            if tts_item.text[match.end():].strip().startswith(str_months):
                return num2words(num, lang='de', to='ordinal')
            else:
                return num

        tts_item.text = re.sub(r'\b[0-9]+\.', replace_number, tts_item.text)

        # Year numbers
        start = 0
        while result := re.search(r'\b[0-9]{4,4}\b', tts_item.text[start:]):
            len_original = 0
            numword = ''
            # When followed by month names
            if tts_item.text[:start + result.span()[0]].strip().endswith(('Jahr', 'in', 'vor', 'nach') + str_months):
                match = tts_item.text[start + result.span()[0]:start + result.span()[1]]

                if int(match) < 2000:
                    len_original = len(match)
                    numword = num2words(match, lang='de', to='year')
                    tts_item.text = tts_item.text[:start + result.span()[0]] + numword + tts_item.text[start + result.span()[1]:]
            start += result.span()[1] - len_original + len(numword)
        return tts_item

    def _prepare_item(self, tts_item: TTS_Item) -> list[TTS_Item]:
        """
        Preprocess the given input TTS item by performing character replacement, splitting, and other operations as needed.

        :param tts_item: The input TTS item to preprocess.
        :type tts_item: TTS_Item

        :return: A list of TTS items resulting from the preprocessing.
        :rtype: list[TTS_Item]
        """

        if tts_item.speaker_idx != -1:
            # try:
            #     speaker_idx = TTS_Arranger.default_speakers.index(tts_item.speaker)
            # except ValueError:
            #     log(LOG_TYPE.ERROR, f'Speaker index "{tts_item.speaker}" is unknown, falling back to default speaker.')
            #     speaker_idx = 0

            if self.model == 'tts_models/de/thorsten/tacotron2-DDC':
                tts_item = self._de_thorsten_tacotron2_DDC_tweaks(tts_item)

            # General preprocessing
            text = tts_item.text

            # Remove Japanese characters etc.
            text = ''.join(filter(lambda character: ord(character) < 0x3000, text))

            # Replace problematic characters, abbreviations etc
            for k, v in self.replace.items():
                text = re.sub(k, v, text)

            tts_item.text = text

            tts_items = [tts_item]

            tts_items = self._break_single(tts_items, r'\n', pause_post_ms=self.pause_newline)
            tts_items = self._break_single(tts_items, r'[;:]\s', pause_post_ms=self.pause_colon)
            tts_items = self._break_single(tts_items, r'[—–]', pause_post_ms=self.pause_dash)
            # tts_items = self._break_single(tts_items, r'[\.!\?]\s', keep=True)
            # tts_items = self.break_single(tts_items, '…')

            # Break items if too long (memory consumption)
            # TODO: disabled for now as recent versions of TTS don’t seem to leak memory that much
            # tts_items = self.find_and_break(tts_items, [
            #                                 '. ', '! ', '? ', ': ', ';', ') ', '] ', '} ', ', ', ' '], self.max_chars)

            # For quotes, use a secondary speaker by shifting the current index up by 1
            # TODO: disabled for now because it breaks the flow too much
            # if self.quotes:
            #     tts_items = self.break_speakers(tts_items, ('“', '”'), True, pause_pre=100, pause_post=100)
            #     tts_items = self.break_speakers(tts_items, ('‘', '’'), True, pause_pre=100, pause_post=100)
            #     tts_items = self.break_speakers(tts_items, ('„', '“'), True, pause_pre=100, pause_post=100)
            #     tts_items = self.break_speakers(tts_items, ('‚', '‘'), True, pause_pre=100, pause_post=100)
            #     tts_items = self.break_speakers(tts_items, ('»', '«'), True, pause_pre=100, pause_post=100)
            #     tts_items = self.break_speakers(tts_items, ('«', '»'), True, pause_pre=100, pause_post=100)
            #     tts_items = self.break_speakers(tts_items, ('"', '"'), True, pause_pre=100, pause_post=100)

            tts_items = self._break_items(tts_items, ('(', ')'), pause_pre_ms=self.pause_parentheses, pause_post_ms=self.pause_parentheses)
            tts_items = self._break_items(tts_items, ('—', '—'), pause_pre_ms=self.pause_parentheses, pause_post_ms=self.pause_parentheses)
            tts_items = self._break_items(tts_items, ('– ', ' –'), pause_pre_ms=self.pause_parentheses, pause_post_ms=self.pause_parentheses)
            # tts_items = self.break_start_end(tts_items, ('- ', ' -'), pause_pre=300, pause_post=300)
            # tts_items = self.break_start_end(tts_items, (r'\s[-–—]-?\s', r'\s[-–—]-?\s'), pause_post=150)
            # tts_items = self.break_start_end(tts_items, (r'\(', r'\)'), pause_post=150)
            tts_items = self._break_items(tts_items, ('*', '*'))

            final_items = []

            for tts_item in tts_items:
                text = tts_item.text

                if not text and tts_item.length > 0:
                    final_items.append(tts_item)

                # text = re.sub(r'([\.\?\!;:]) ', r'\1\n', text)
                text = re.sub(r'[–—]', r'-', text)
                text = re.sub(r'[„“”]', r'"', text)
                text = re.sub(r'[‘’]', r"'", text)

                # Remove all remaining punctuation after first occurrence
                # text = re.sub(r'([\.\?\!;:])\s?[\.\?\!;:,\)\"\'.\]]+', r'\1', text)
                text = text.rstrip(string.punctuation + ' ')

                # Strip starting punctuation and normalize ending punctuation
                text = text.strip().lstrip(string.punctuation).strip()

                if self.model != 'tts_models/en/vctk/vits':
                    # Add a full stop if necessary to avoid synthesizing problems with some models
                    text = re.sub(r'([a-zA-Z0-9])$', r'\1.', text)

                if len(text) > 0:
                    if re.search(r'[a-zA-Z0-9]', text):
                        tts_item.text = text
                        final_items.append(tts_item)

                        if text[-1] in ['.', ':']:
                            final_items.append(TTS_Item(length=self.pause_sentence))
                        elif text[-1] in ['!', '?']:
                            final_items.append(TTS_Item(length=self.pause_question_exclamation))

            # if len(final_items) > 0:
            #     tts_items[-1].properties.pause_pre += pause_pre
            #     tts_items[-1].properties.pause_post += pause_post
        else:
            final_items = [tts_item]

        return final_items

    def _break_single(self, tts_items: list[TTS_Item], break_at: str, keep: bool = False, pause_post_ms: int = 0) -> list[TTS_Item]:
        """
        Break the given list of input TTS items at the specified single character and return a list of resulting input TTS items.

        :param tts_items: The list of input TTS items to break.
        :type tts_items: list[TTS_Item]

        :param break_at: The single character at which to break the input TTS items.
        :type break_at: str

        :param keep: Whether to keep the breaking character in the resulting TTS items. Default is False.
        :type keep: bool

        :param pause_post: The duration of a pause (in ms) to insert after each broken TTS item. Default is 0.
        :type pause_post: int

        :return: A list of TTS items resulting from the breaking.
        :rtype: list[TTS_Item]
        """
        final_items = []

        for tts_item in tts_items:
            text = tts_item.text

            if not text and tts_item.length > 0:
                final_items.append(tts_item)

            last_start = 0

            if break_at:
                matches = re.finditer('(.*?)' + break_at, text)

                for m in matches:
                    length = 0
                    if keep == False:
                        length = m.regs[0][1] - m.regs[1][1]

                    item_text = text[m.start():m.end() - length]

                    if item_text:

                        # From last group to end of current group
                        final_items.append(TTS_Item(item_text, tts_item.speaker, tts_item.speaker_idx, tts_item.length))
                        if pause_post_ms > 0:
                            final_items.append(TTS_Item(length=pause_post_ms))
                        last_start = m.end()

                # From end of last group to end of text
                text = text[last_start:].strip()

                if text:
                    final_items.append(TTS_Item(text, tts_item.speaker, tts_item.speaker_idx, tts_item.length))

        return final_items

    def _get_character(self, text: str, pos: int) -> str:
        """
        Get the character at the specified position in the given string and return it as a string.

        :param text: The string to get the character from.
        :type text: str

        :param pos: The position of the character to get.
        :type pos: int

        :return: The character at the specified position, or an empty string if the position is out of bounds.
        :rtype: str
        """
        if 0 <= pos < len(text):
            return text[pos]
        return ''

    def _break_items(self, tts_items: list[TTS_Item], start_end: tuple = (), pause_pre_ms: int = 0, pause_post_ms: int = 0) -> list[TTS_Item]:
        """
        Break items in a list of TTS items based on opening and closing characters (like parenthesis) and return a new list.

        :param tts_items: A list of TTS items to be broken down.
        :type tts_items: list[TTS_Item]

        :param start_end: A tuple of the opening and closing characters used to break down the items, defaults to ().
        :type start_end: tuple[int, int]

        :param pause_pre_ms: The duration of a pause (in ms) to be inserted before the opening character, defaults to 0.
        :type pause_pre_ms: int

        :param pause_post_ms: The duration of a pause (in ms) to be inserted after the closing character, defaults to 0.
        :type pause_post_ms: int

        :return: A new list of TTS items that have been broken down based on the specified opening and closing characters.
        :rtype: list[TTS_Item]
        """
        final_items = []

        if tts_items:
            length = len(start_end[0])

            opened = False
            current_speaker = ''
            current_speaker_idx = 0

            for tts_item in tts_items:
                pos = 0

                found = False

                if not tts_item.text and tts_item.length > 0:
                    final_items.append(tts_item)

                # print(f'New item: {tts_item.text} / {tts_item.speaker}')

                for idx, c in enumerate(tts_item.text):
                    new_item = copy.copy(tts_item)
                    new_item.text = tts_item.text[pos:idx].strip()
                    new_item.speaker = tts_item.speaker
                    current_speaker = tts_item.speaker
                    current_speaker_idx = tts_item.speaker_idx

                    add_item = False

                    # print(f'idx: {idx}')
                    # print(f'c: {c}')
                    # print(f'tts_item: {tts_item.text}')

                    if start_end[0] == start_end[1]:
                        # If open and closing pattern are the same
                        if c in start_end:
                            if not opened:
                                if self._get_character(tts_item.text, idx - 1) in string.punctuation + ' ':
                                    opened = True
                                    add_item = True
                                    # print(f'Open')
                            else:
                                if self._get_character(tts_item.text, idx + 1) in string.punctuation + ' ':
                                    opened = False
                                    add_item = True
                                    # print(f'Close')
                        elif c in ['.', ',', ';', ':']:
                            # Attach closing punctuation to last text segment
                            if pos == idx:
                                if len(final_items) > 0:
                                    final_items[-1].text += c
                                    pos += length
                    else:
                        # If open and closing pattern are not the same
                        if c == start_end[0]:
                            if self._get_character(tts_item.text, idx - 1) in string.punctuation + ' ':
                                add_item = True
                                # print(f'Open')
                        elif c == start_end[1]:
                            if self._get_character(tts_item.text, idx + 1) in string.punctuation + ' ':
                                add_item = True

                                if pause_pre_ms > 0:
                                    final_items.append(TTS_Item(length=pause_pre_ms))

                                # print(f'Close')
                        elif c in ['.', ',', ';', ':']:
                            if pos == idx:
                                if len(final_items) > 0:
                                    final_items[-1].text += c
                                    pos += length

                    if add_item:
                        # Add item resulting from breaking
                        if new_item.text:
                            # if len(final_items) > 0:
                            #     if pause_pre > 0:
                            #         final_items.append(TTS_Item(length=pause_pre))

                            final_items.append(new_item)

                            # if len(final_items) > 2:
                            #     if pause_post > 0:
                            #         final_items.append(TTS_Item(length=pause_post))
                            # print(f'Adding item after breaking: {new_item.text} / {new_item.speaker}')
                        pos = idx + 1
                        found = add_item

                if found:
                    if pause_post_ms > 0:
                        final_items.append(TTS_Item(length=pause_post_ms))

                # Add rest / regular item
                new_item = copy.copy(tts_item)
                new_item.text = tts_item.text[pos:].strip()
                new_item.speaker = current_speaker
                new_item.speaker_idx = current_speaker_idx
                new_item.length = tts_item.length

                if new_item.text:
                    # print(f'Adding regular item: {new_item.text} / {new_item.speaker}')
                    final_items.append(new_item)

        return final_items

    def preprocess_items(self, tts_items: list[TTS_Item]) -> list[TTS_Item]:
        """
        Preprocesses a list of TTS items.

        :param tts_items: A list of TTS items to be preprocessed.
        :type tts_items: list[TTS_Item]

        :return: A new list of preprocessed TTS items.
        :rtype: list[TTS_Item]
        """
        final_items = []
        merged_items = self._merge_similar_items(tts_items)

        for tts_item in merged_items:
            final_items += self._prepare_item(tts_item)

        return final_items

    def _merge_similar_items(self, items=[]) -> list:
        """
        Merge similar items for smoother synthesizing and avoiding unwanted pauses

        :param items: A list of TTS items to merge
        :type items: list

        :return: A list of merged TTS items
        :rtype: list
        """
        final_items: list[TTS_Item] = []

        if items:
            start_item = -1
            merged_item = TTS_Item()

            for i, item in enumerate(items):
                if start_item < 0:
                    # Scanning not started
                    start_item = i
                    merged_item = item
                else:
                    # Scanning started
                    if merged_item.speaker == item.speaker and merged_item.speaker_idx == item.speaker_idx:
                        # Starting item and current are similar, add to merge item text and length
                        if merged_item.text and item.text:
                            merged_item.text += ' ' + item.text
                        merged_item.length += item.length
                    else:
                        # Starting item and current are not similar, add last and current item, set this item as new starting item
                        if final_items:
                            if final_items[-1] != merged_item:
                                final_items.append(merged_item)
                        else:
                            final_items.append(merged_item)
                        final_items.append(item)
                        merged_item = item
                        start_item = i

                if i == len(items) - 1:
                    if final_items:
                        if final_items[-1] != merged_item:
                            final_items.append(merged_item)
                    else:
                        final_items.append(merged_item)

        return final_items

    def synthesize_and_write(self, tts_items: list[TTS_Item], output_filename: str, callback: Callable[[int, int], None] | None = None):
        """
        Synthesize and write list of items as an audio file

        :param tts_items: List of TTS items to be synthesized
        :type tts_items: list

        :param output_filename: Absolute path and filename of output audio file including file type extension (for example mp3, ogg)
        :type output_filename: str

        :param callback: Reference to function to be called after synthesizing of an item is finished
        :type callback: function

        :return: None
        :rtype: None
        """
        time_total = 0.0
        time_needed = 0.0

        characters_sum = 0
        characters_total = 0

        tts_items = self.preprocess_items(tts_items)

        for tts_item in tts_items:
            characters_sum += len(tts_item.text)

        segments = AudioSegment.empty()

        for idx, tts_item in enumerate(tts_items):
            if tts_item.text:
                log(LOG_TYPE.INFO, f'Synthesizing item {idx + 1} of {len(tts_items)} "({tts_item.speaker}", {tts_item.speaker_idx}, {tts_item.length}ms):{bcolors.ENDC} {tts_item.text}')
            else:
                log(LOG_TYPE.INFO, f'Adding pause: {tts_item.length}ms:{bcolors.ENDC} {tts_item.text}')

            if time_needed:
                log(LOG_TYPE.INFO, f'(Remaining time: {str(datetime.timedelta(seconds=round(time_needed)))})')

            time_last = time.time()

            try:
                segments += self.synthesize_tts_item(tts_item)

                time_now = time.time()
                time_total += time_now - time_last
                characters_total += len(tts_item.text)

                if characters_total > 0:
                    time_needed = ((time_total / characters_total) * characters_sum) - time_total

                # Report progress
                if callback is not None:
                    callback(idx, len(tts_items))
            except KeyboardInterrupt:
                log(LOG_TYPE.ERROR, 'Stopped by user.')
                sys.exit()
            except Exception as e:
                # with open(self.temp_dir.name + '/tts-error.log', 'a+') as f:
                #     f.write(f'Error synthesizing "{output_filename}"\n')
                log(LOG_TYPE.ERROR, f'Error synthesizing "{output_filename}": {e}')
                sys.exit()

        self.write(segments, output_filename)

    def synthesize_tts_item(self, tts_item: TTS_Item) -> AudioSegment:
        """
        Synthesize a single item and return a PyDub AudioSegment object

        :param tts_item: TTS item to be synthesized
        :type tts_item: TTS_Item

        :return: AudioSegment object of synthesized audio
        :rtype: AudioSegment
        """
        segment = AudioSegment.empty()

        if tts_item.text:
            try:
                speaker = ''

                if self.synthesizer.tts_model and self.synthesizer.tts_model.num_speakers > 1:
                    speaker = tts_item.speaker or self.speakers[tts_item.speaker_idx % len(self.speakers)]
                    speaker = self.preferred_speakers[tts_item.speaker_idx % len(self.preferred_speakers)] if self.preferred_speakers and speaker in self.speakers else speaker

                # Suppress tts output
                with contextlib.redirect_stdout(None):
                    wav = self.synthesizer.tts(
                        text=tts_item.text,
                        speaker_name=speaker,
                    )
            except Exception as e:
                raise Exception(f'Error synthesizing "{tts_item.text}: {e}"')
            else:
                speech_segment = numpy_to_segment(np.array(wav), int(self.synthesizer.output_sample_rate))

                # If length is predefined, add padding if necessary
                if int(speech_segment.duration_seconds * 1000) < tts_item.length:
                    speech_segment += AudioSegment.silent(int(tts_item.length - speech_segment.duration_seconds * 1000), int(self.synthesizer.output_sample_rate))
                else:
                    # Strip some silence away to make pauses easier to control
                    silence = detect_silence(speech_segment, min_silence_len=self.silence_length, silence_thresh=self.silence_threshold)
                    speech_segment = speech_segment[:silence[-1][0]]

                if isinstance(speech_segment, AudioSegment):
                    speech_segment = speech_segment.apply_gain(-20 - speech_segment.dBFS)

                segment += speech_segment
        else:
            if tts_item.length > 0:
                segment += AudioSegment.silent(tts_item.length, int(self.synthesizer.output_sample_rate))

        return segment

    def write(self, segment: AudioSegment, output_filename: str) -> None:
        """
        Compress, convert and write AudioSegment as a given output file path and name

        :param segment: AudioSegment to be written
        :type segment: AudioSegment

        :param output_filename: Absolute path and filename of output audio file including file type extension (for example mp3, ogg)
        :type output_filename: str

        :return: None
        :rtype: None
        """
        # Clean up to free up some memory
        # self.synthesizer = None
        # gc.collect()

        # Set default format to mp3
        format = os.path.splitext(output_filename)[1][1:] or 'mp3'

        folder = os.path.dirname(os.path.abspath(output_filename))

        os.makedirs(folder, exist_ok=True)

        # Ensure output file name has a file extension
        output_filename = os.path.splitext(output_filename)[0] + '.' + format

        log(LOG_TYPE.INFO, f'Compressing, converting and saving as {output_filename}')

        comp_expansion = 12.5
        comp_raise = 0.0001

        # Apply dynamic compression
        # segment.export(output_filename, format, parameters=['-filter', 'speechnorm=e=25:r=0.0001:l=1', '-filter', 'loudnorm=tp=-1.0:offset=7'])
        params = ['-filter', f'speechnorm=e={comp_expansion}:r={comp_raise}:l=1']
        bitrate = '320k' if format == 'mp3' else None
        segment.export(output_filename, format, parameters=params, bitrate=bitrate)
