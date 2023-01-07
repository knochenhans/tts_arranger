import contextlib
import copy
import datetime
import gc
import io
import os
import re
import string
import sys
import time
from dataclasses import dataclass
from enum import Enum, auto
from math import isclose

import numpy
import numpy as np
import scipy.io.wavfile
import TTS
from pydub import AudioSegment
from pydub.effects import normalize
from pydub.silence import detect_silence
from TTS.utils.manage import ModelManager
from TTS.utils.synthesizer import Synthesizer


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class LOG_TYPE(Enum):
    INFO = auto()
    WARNING = auto()
    ERROR = auto()


def log(log_type: LOG_TYPE, message: str):
    format = f'{bcolors.ENDC}'

    if log_type == LOG_TYPE.INFO:
        format = f'{bcolors.HEADER}'
    elif log_type == LOG_TYPE.WARNING:
        format = f'{bcolors.WARNING}'
    elif log_type == LOG_TYPE.ERROR:
        format = f'{bcolors.FAIL}'

    print(format + message + f'{bcolors.ENDC}')


@dataclass
class TTS_Item_Properties:
    speaker: str = ''
    # speaker_idx: int
    pause_pre: int = 0
    pause_post: int = 0
    # notes = notes


@dataclass
class TTS_Item:
    text: str = ''
    properties: TTS_Item_Properties = TTS_Item_Properties()


class TTS_Convert:
    # Speakers in preferred order (usually #0 and #1 for normal and quote speaker)
    # Best speakers: p293, p330, p273
    default_speakers = []

    # Break lines after number of characters to avoid OOM
    max_chars = 320

    def __init__(self, speakers=None, model='tts_models/en/vctk/vits', vocoder='', multi=True) -> None:
        self.model = model
        self.vocoder = vocoder
        self.multi = multi
        self.silence_length = 100
        self.silence_threshold = -60

        # self.quotes = quotes
        self.current_speaker_idx = 0

        if not self.default_speakers:
            with open(os.path.dirname(os.path.realpath(__file__)) + '/speakers', 'r') as speaker_file:
                self.default_speakers = speaker_file.read().split()

        if speakers:
            self.default_speakers = speakers

        self.replace = {}

        # Load general replace list
        with open(os.path.dirname(os.path.realpath(__file__)) + '/replace.csv', 'r') as file:
            reader = csv.reader(file, delimiter='\t')
            for row in reader:
                self.replace[row[0]] = row[1]

        # Load language specific replace list
        lang = 'en'

        model_splitted = model.split('/')

        if model_splitted:
            if len(model_splitted) >= 2: 
                lang = model_splitted[1]
            
        with open(os.path.dirname(os.path.realpath(__file__)) + f'/replace_{lang}.csv', 'r') as file:
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

            vocoder_path = None
            vocoder_config_path = None

            if self.vocoder:
                vocoder_path, vocoder_config_path, _ = self.manager.download_model(self.vocoder)

            self.synthesizer = Synthesizer(
                tts_checkpoint=model_path,
                tts_config_path=config_path,
                tts_speakers_file=None,
                tts_languages_file=None,
                vocoder_checkpoint=vocoder_path,
                vocoder_config=vocoder_config_path,
                encoder_checkpoint=None,
                encoder_config=None,
                use_cuda=False,
            )

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
        pause_pre = tts_item.properties.pause_post
        pause_post = tts_item.properties.pause_post

        # try:
        #     speaker_idx = TTS_Convert.default_speakers.index(tts_item.speaker)
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

        tts_items = self._break_single(tts_items, r'\n', pause_post=250)
        tts_items = self._break_single(tts_items, r'[;:]\s', pause_post=150)
        tts_items = self._break_single(tts_items, r'[—–]', pause_post=300)
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

        tts_items = self._break_items(tts_items, ('(', ')'), pause_pre=300, pause_post=300)
        tts_items = self._break_items(tts_items, ('—', '—'), pause_pre=300, pause_post=300)
        tts_items = self._break_items(tts_items, ('– ', ' –'), pause_pre=300, pause_post=300)
        # tts_items = self.break_start_end(tts_items, ('- ', ' -'), pause_pre=300, pause_post=300)
        # tts_items = self.break_start_end(tts_items, (r'\s[-–—]-?\s', r'\s[-–—]-?\s'), pause_post=150)
        # tts_items = self.break_start_end(tts_items, (r'\(', r'\)'), pause_post=150)
        tts_items = self._break_items(tts_items, ('*', '*'))

        for tts_item in tts_items:
            text = tts_item.text

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
                if text[-1] in ['.', ':', '!']:
                    tts_item.properties.pause_post = 500
                elif text[-1] in ['?']:
                    tts_item.properties.pause_post = 750
                tts_item.text = text

        if len(tts_items) > 0:
            tts_items[-1].properties.pause_post += 500
            tts_items[-1].properties.pause_pre += pause_pre
            tts_items[-1].properties.pause_post += pause_post

        # Final check if text still contains actual speech date (to exclude single '"' etc.)
        final_items = []

        for tts_item in tts_items:
            if re.search(r'[a-zA-Z0-9]', tts_item.text):
                final_items.append(tts_item)

        return final_items

    def _break_single(self, tts_items: list[TTS_Item], break_at: str, keep: bool = False, pause_post: int = 0) -> list[TTS_Item]:
        final_items = []

        for tts_item in tts_items:
            text = tts_item.text

            last_start = 0

            if break_at:
                matches = re.finditer('(.*?)' + break_at, text)

                for m in matches:
                    length = 0
                    if keep == False:
                        length = m.regs[0][1] - m.regs[1][1]

                    item = TTS_Item(text[m.start():m.end() - length])

                    # From last group to end of current group
                    final_items.append(TTS_Item(text[m.start():m.end() - length], TTS_Item_Properties(speaker=tts_item.properties.speaker, pause_post=pause_post)))
                    last_start = m.end()

                # From end of last group to end of text
                text = text[last_start:].strip()

                if text:
                    final_items.append(TTS_Item(text, TTS_Item_Properties(tts_item.properties.speaker, tts_item.properties.pause_pre, tts_item.properties.pause_post)))

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
            current_speaker = self.default_speakers[0]

            for tts_item in tts_items:
                pos = 0

                # print(f'New item: {tts_item.text} / {tts_item.speaker}')

                for idx, c in enumerate(tts_item.text):
                    new_item = copy.copy(tts_item)
                    new_item.text = tts_item.text[pos:idx].strip()
                    new_item.properties.speaker = tts_item.properties.speaker
                    current_speaker = tts_item.properties.speaker

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
                            # Attach closing punctuation too last text segment
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
                                # print(f'Close')
                        elif c in ['.', ',', ';', ':']:
                            if pos == idx:
                                if len(final_items) > 0:
                                    final_items[-1].text += c
                                    pos += lenght

                    if add_item:
                        # Add item resulting from breaking
                        if new_item.text:
                            new_item.properties.pause_pre = pause_pre
                            new_item.properties.pause_post = pause_post
                            final_items.append(new_item)
                            # print(f'Adding item after breaking: {new_item.text} / {new_item.speaker}')
                        pos = idx + 1

                # Add rest / regular item
                new_item = copy.copy(tts_item)
                new_item.text = tts_item.text[pos:].strip()
                new_item.properties.speaker = current_speaker

                if new_item.text:
                    # print(f'Adding regular item: {new_item.text} / {new_item.speaker}')
                    final_items.append(new_item)

        return final_items

    #TODO: Is this still needed?
    # def convert_to_audiosegment(self, tts_items: list[TTS_Item]) -> AudioSegment:
    #     final_items = self.preprocess_items(tts_items)

    #     segments = AudioSegment.empty()

    #     for tts_item in final_items:
    #         segments += self.synthesize_tts_item(tts_item)

    #     return segments

    def preprocess_items(self, tts_items: list[TTS_Item]) -> list[TTS_Item]:
        final_items = []

        for tts_item in tts_items:
            if tts_item.text:
                final_items += self._prepare_item(tts_item)

        #log(LOG_TYPE.INFO, f'{len(tts_items)} items broken down into {len(final_items)} items')

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
            log(LOG_TYPE.INFO,
                f'Synthesizing item {idx + 1} of {len(tts_items)} ({tts_item.properties.speaker}, {tts_item.properties.pause_pre}|{tts_item.properties.pause_post}):{bcolors.ENDC} {tts_item.text}')

            if time_needed:
                log(LOG_TYPE.INFO, f'(Remaining time: {str(datetime.timedelta(seconds=round(time_needed)))})')

            time_last = time.time()

            try:
                segments += self.synthesize_tts_item(tts_item)

                time_now = time.time()
                time_total += time_now - time_last
                characters_total += len(tts_item.text)

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
        if tts_item.properties.pause_pre > 0:
            segment += AudioSegment.silent(duration=tts_item.properties.pause_pre)

        try:
            # Suppress tts output

            speaker = None

            if self.multi:
                speaker = tts_item.properties.speaker

            with contextlib.redirect_stdout(None):
                wav = self.synthesizer.tts(
                    text=tts_item.text,
                    speaker_name=speaker,
                    speaker_wav=None,
                    language_name=None,
                    reference_wav=None,
                    reference_speaker_name=None,
                )
        except Exception as e:
            # with open(self.temp_dir.name + '/tts-error.log', 'a+') as f:
            #     f.write(f'Error synthesizing "{tts_item.text}"\n')

            raise Exception(f'Error synthesizing {tts_item.text}: {e}')
        else:
            speech_segment = self._numpy_to_segment(wav)

            # Strip some silence away to make pauses easier to control
            silence = detect_silence(speech_segment, min_silence_len=self.silence_length, silence_thresh=self.silence_threshold)
            speech_segment = speech_segment[:silence[-1][0]]

            if isinstance(speech_segment, AudioSegment):
                speech_segment = speech_segment.apply_gain(-20 - speech_segment.dBFS)

            segment += speech_segment

        if tts_item.properties.pause_post > 0:
            segment += AudioSegment.silent(duration=tts_item.properties.pause_post)

        return segment

    def _numpy_to_segment(self, numpy_wav) -> AudioSegment:
        # Convert tts output wave into pydub segment
        wav = numpy.array(numpy_wav).astype(numpy.float32)
        wav_io = io.BytesIO()
        scipy.io.wavfile.write(wav_io, self.synthesizer.output_sample_rate, wav)
        wav_io.seek(0)
        return AudioSegment.from_wav(wav_io)

    def _segment_to_numpy(self, segment):
        samples = [s.get_array_of_samples() for s in segment.split_to_mono()]

        fp_arr = np.array(samples).T.astype(np.float64)
        fp_arr /= np.iinfo(samples[0].typecode).max

        return fp_arr

    def _compress(self, threshold: float, ratio: float, makeup: float, attack: float, release: float, segment: AudioSegment) -> AudioSegment:
        if ratio < 1.0:
            print('Ratio must be > 1.0 for compression to occur! You are expanding.')
        if ratio == 1.0:
            print('Signal is unaffected.')

        data = self._segment_to_numpy(segment)

        try:
            ch = len(data[0, ])
        except:
            ch = 1

        if ch == 1:
            data = data.reshape(-1, 1)
        n = len(data)

        data[np.where(data == 0)] = 0.00001

        data_dB = 20 * np.log10(abs(data))

        dataC = data_dB.copy()

        a = np.exp(-np.log10(9) / (44100 * attack * 1.0E-3))
        re = np.exp(-np.log10(9) / (44100 * release * 1.0E-3))

        log(LOG_TYPE.INFO, '(1/3)')

        for k in range(ch):
            for i in range(n):
                if dataC[i, k] > threshold:
                    dataC[i, k] = threshold + (dataC[i, k] - threshold) / (ratio)

        gain = np.zeros(n)
        sgain = np.zeros(n)

        gain = np.subtract(dataC, data_dB)
        sgain = gain.copy()

        log(LOG_TYPE.INFO, '(2/3)')

        for k in range(ch):
            for i in range(1, n):
                if sgain[i - 1, k] >= sgain[i, k]:
                    sgain[i, k] = a * sgain[i - 1, k] + (1 - a) * sgain[i, k]
                if sgain[i - 1, k] < sgain[i, k]:
                    sgain[i, k] = re*sgain[i - 1, k] + (1 - re)*sgain[i, k]

        dataCs = np.zeros(n)
        dataCs = data_dB + sgain + makeup

        dataCs_bit = 10.0 ** ((dataCs) / 20.0)

        log(LOG_TYPE.INFO, '(3/3)')

        for k in range(ch):
            for i in range(n):
                if data[i, k] < 0.0:
                    dataCs_bit[i, k] = -1.0 * dataCs_bit[i, k]

        return self._numpy_to_segment(dataCs_bit)

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
        segment = self._compress(-20.0, 4.0, 4.5, 5.0, 15.0, segment)
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
