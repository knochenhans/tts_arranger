import contextlib
import copy
import csv
import datetime
import os
import re
import string
import sys
import time
from dataclasses import dataclass

import TTS
from pydub import AudioSegment
from pydub.effects import normalize
from pydub.silence import detect_silence
from TTS.utils.manage import ModelManager
from TTS.utils.synthesizer import Synthesizer

from audio import compress, numpy_to_segment
from log import LOG_TYPE, bcolors, log


@dataclass
class TTS_Item:
    text: str = ''
    speaker: str = ''
    speaker_idx: int = 0
    length: int = 0

    def __post_init__(self):
        # Mark pauses by invalidating speaker index
        if self.text == '' and self.length > 0:
            self.speaker_idx = -1


class TTS_Arranger:
    def __init__(self, model='tts_models/en/vctk/vits', vocoder='', preferred_speakers=None) -> None:
        self.model = model
        self.vocoder = vocoder
        self.silence_length = 100
        self.silence_threshold = -60
        # self.pause_post_regular =

        # self.quotes = quotes
        self.current_speaker_idx = 0

        self.speakers = []

        # Config
        self.pause_sentence = 750
        self.pause_question_exclamation = 1000
        self.pause_parentheses = 300
        self.pause_dash = 300
        self.pause_newline = 250
        self.pause_colon = 100

        if not preferred_speakers:
            preferred_speakers = []

        self.preferred_speakers = []

        # if not self.default_speakers:
        #     with open(os.path.dirname(os.path.realpath(__file__)) + '/speakers', 'r') as speaker_file:
        #         self.default_speakers = speaker_file.read().split()

        # if speakers:
        #     self.default_speakers = speakers

        self.replace = {}

        # Load general replace list
        with open(os.path.dirname(os.path.realpath(__file__)) + '/replace', 'r') as file:
            reader = csv.reader(file, delimiter='\t')
            for row in reader:
                self.replace[row[0]] = row[1]

        # Load language specific replace list
        lang = 'en'

        model_splitted = model.split('/')

        if model_splitted:
            if len(model_splitted) >= 2:
                lang = model_splitted[1]

        with open(os.path.dirname(os.path.realpath(__file__)) + f'/replace_{lang}', 'r') as file:
            reader = csv.reader(file, delimiter='\t')
            for row in reader:
                self.replace[row[0]] = row[1]

    # def __del__(self):
    #     self.temp_dir.cleanup()
    #     self.synthesizer = None
    #     gc.collect()

    def initialize(self):
        log(LOG_TYPE.INFO, f'Initializing speech synthesizer')

        self.manager = ModelManager(os.path.dirname(TTS.__file__) + '/.models.json')

        with contextlib.redirect_stdout(None):
            model_path, config_path, model_item = self.manager.download_model(self.model)

            vocoder_path = ''
            vocoder_config_path = ''

            if self.vocoder:
                vocoder_path, vocoder_config_path, _ = self.manager.download_model(self.vocoder)

            self.synthesizer = Synthesizer(
                tts_checkpoint=model_path,
                tts_config_path=config_path,
                vocoder_checkpoint=vocoder_path,
                vocoder_config=vocoder_config_path,
            )

            # Get speaker list from model
            if self.synthesizer.tts_model:
                if self.synthesizer.tts_model.num_speakers > 1:
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

    def _minimize_tailing_punctuation(self, text: str) -> str:
        lenght = 0

        for i in reversed(text):
            if i in string.punctuation + ' ':
                lenght += 1
            else:
                return text[:len(text) - (lenght - 1)]
        return text

    def _prepare_item(self, tts_item: TTS_Item) -> list[TTS_Item]:
        # try:
        #     speaker_idx = TTS_Arranger.default_speakers.index(tts_item.speaker)
        # except ValueError:
        #     log(LOG_TYPE.ERROR, f'Speaker index "{tts_item.speaker}" is unknown, falling back to default speaker.')
        #     speaker_idx = 0

        # Some general preprocessing

        text = tts_item.text

        # Remove Japanese characters etc.
        text = ''.join(filter(lambda character: ord(character) < 0x3000, text))

        # Replace problematic characters, abbreviations etc
        for k, v in self.replace.items():
            text = re.sub(k, v, text)

        tts_item.text = text

        tts_items = [tts_item]

        tts_items = self._break_single(tts_items, r'\n', pause_post=self.pause_newline)
        tts_items = self._break_single(tts_items, r'[;:]\s', pause_post=self.pause_colon)
        tts_items = self._break_single(tts_items, r'[—–]', pause_post=self.pause_dash)
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

        tts_items = self._break_items(tts_items, ('(', ')'), pause_pre=self.pause_parentheses, pause_post=self.pause_parentheses)
        tts_items = self._break_items(tts_items, ('—', '—'), pause_pre=self.pause_parentheses, pause_post=self.pause_parentheses)
        tts_items = self._break_items(tts_items, ('– ', ' –'), pause_pre=self.pause_parentheses, pause_post=self.pause_parentheses)
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
            text = self._minimize_tailing_punctuation(text)

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

        return final_items

    def _break_single(self, tts_items: list[TTS_Item], break_at: str, keep: bool = False, pause_post: int = 0) -> list[TTS_Item]:
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
                        if pause_post > 0:
                            final_items.append(TTS_Item(length=pause_post))
                        last_start = m.end()

                # From end of last group to end of text
                text = text[last_start:].strip()

                if text:
                    final_items.append(TTS_Item(text, tts_item.speaker, tts_item.speaker_idx, tts_item.length))

        return final_items

    def _get_character(self, text: str, pos: int) -> str:
        character = ''

        if pos > 0 and pos < len(text):
            character = text[pos]
        return character

    def _break_items(self, tts_items: list[TTS_Item], start_end: tuple = (), pause_pre: int = 0, pause_post: int = 0) -> list[TTS_Item]:
        final_items = []

        if tts_items:
            lenght = len(start_end[0])

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
                                    pos += lenght
                    else:
                        # If open and closing pattern are not the same
                        if c == start_end[0]:
                            if self._get_character(tts_item.text, idx - 1) in string.punctuation + ' ':
                                add_item = True
                                # print(f'Open')
                        elif c == start_end[1]:
                            if self._get_character(tts_item.text, idx + 1) in string.punctuation + ' ':
                                add_item = True

                                if pause_pre > 0:
                                    final_items.append(TTS_Item(length=pause_pre))

                                # print(f'Close')
                        elif c in ['.', ',', ';', ':']:
                            if pos == idx:
                                if len(final_items) > 0:
                                    final_items[-1].text += c
                                    pos += lenght

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
                    if pause_post > 0:
                        final_items.append(TTS_Item(length=pause_post))

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
        final_items = []

        for tts_item in tts_items:
            final_items += self._prepare_item(tts_item)

        #log(LOG_TYPE.INFO, f'{len(tts_items)} items broken down into {len(final_items)} items')

        return self._merge_similar_items(final_items)

    def _merge_similar_items(self, items=[]) -> list:
        final_items = []

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
                        merged_item.text += item.text
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

    def synthesize_and_export(self, tts_items: list[TTS_Item], output_filename: str, callback=None):
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
                log(LOG_TYPE.INFO, f'Synthesizing item {idx + 1} of {len(tts_items)} ({tts_item.speaker}, {tts_item.length}ms):{bcolors.ENDC} {tts_item.text}')
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
                if callback:
                    callback(idx, len(tts_items))
            except KeyboardInterrupt:
                log(LOG_TYPE.ERROR, 'Stopped by user.')
                sys.exit()
            except Exception as e:
                # with open(self.temp_dir.name + '/tts-error.log', 'a+') as f:
                #     f.write(f'Error synthesizing "{output_filename}"\n')
                log(LOG_TYPE.ERROR, f'Error synthesizing "{output_filename}": {e}')
                sys.exit()

        self.export(segments, output_filename)

    def synthesize_tts_item(self, tts_item: TTS_Item) -> AudioSegment:
        segment = AudioSegment.empty()
        # if self.synthesizer is not None:
        if tts_item.text:
            try:
                # Suppress tts output

                speaker = ''

                if self.synthesizer.tts_model:
                    if self.synthesizer.tts_model.num_speakers > 1:
                        speaker = tts_item.speaker

                        # Use index if no explicit speaker name is given, wrap around speakers to avoid undefined indexes
                        if not speaker:
                            speaker = self.speakers[tts_item.speaker_idx % len(self.speakers)]

                            if self.preferred_speakers:
                                # if len(self.preferred_speakers) >= tts_item.speaker_idx:
                                if self.preferred_speakers[tts_item.speaker_idx % len(self.preferred_speakers)] in self.speakers:
                                    speaker = self.preferred_speakers[tts_item.speaker_idx % len(self.preferred_speakers)]

                with contextlib.redirect_stdout(None):
                    wav = self.synthesizer.tts(
                        text=tts_item.text,
                        speaker_name=speaker,
                    )
            except Exception as e:
                # with open(self.temp_dir.name + '/tts-error.log', 'a+') as f:
                #     f.write(f'Error synthesizing "{tts_item.text}"\n')

                raise Exception(f'Error synthesizing "{tts_item.text}: {e}"')
            else:
                speech_segment = numpy_to_segment(wav, int(self.synthesizer.output_sample_rate))

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

    def export(self, segment: AudioSegment, output_filename: str) -> None:
        # Clean up to free up some memory
        # self.synthesizer = None
        # gc.collect()

        # Set default format to mp3
        format = 'mp3'

        file_format = os.path.splitext(output_filename)[1][1:]

        if file_format:
            format = file_format

        log(LOG_TYPE.INFO, f'Applying compression:')
        segment = compress(-20.0, 4.0, 4.5, 5.0, 15.0, segment, self.synthesizer.output_sample_rate)
        # self.audio = normalize(compress_dynamic_range(
        #     self.audio, threshold=-20, release=15))

        log(LOG_TYPE.INFO, f'Compressing, converting and saving as {output_filename}')
        audio_normalized = normalize(segment)

        folder = os.path.dirname(os.path.abspath(output_filename))

        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        if format == 'mp3':
            audio_normalized.export(output_filename, format=format, bitrate='320k')
        else:
            audio_normalized.export(output_filename, format=format)
