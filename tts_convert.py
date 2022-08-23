import contextlib
import copy
import datetime
from enum import Enum, auto
import gc
from math import isclose
import os
import re
import string
import sys
import numpy as np
from pydub import AudioSegment
from pydub.silence import detect_silence
from pydub.effects import normalize
import TTS
from TTS.utils.manage import ModelManager
from TTS.utils.synthesizer import Synthesizer
import time
import numpy
import io
import scipy.io.wavfile


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


class TTS_Item:
    def __init__(self, text: str = '', speaker: str = '', pause_pre: int = 0, pause_post: int = 0, strip_silence: bool = True, speaker_idx: int = -1):
        self.text = text
        self.speaker = speaker
        self.speaker_idx = speaker_idx
        self.pause_pre = pause_pre
        self.pause_post = pause_post
        self.strip_silence = strip_silence

    def get_character_count(self) -> int:
        return len(self.text)

    # def speak(self, synthesizer: Synthesizer, path='/tmp/') -> AudioSegment:
    #     audio = AudioSegment.empty()

    #     if synthesizer is not None:
    #         if self.pause_pre > 0:
    #             audio += AudioSegment.silent(duration=self.pause_pre)

    #         # Check if line contains actual speech data
    #         # TODO: put into prepare
    #         # if re.search(r'[a-zA-Z0-9]', self.text):
    #         try:
    #             # Suppress tts output
    #             with contextlib.redirect_stdout(None):
    #                 wav = synthesizer.tts(
    #                     text=self.text,
    #                     speaker_name=self.speaker,
    #                     speaker_wav=None,
    #                     language_name='',
    #                     reference_wav=None,
    #                     reference_speaker_name=None,
    #                 )
    #         except:
    #             # with open(path + 'tts-error.log', 'a+') as f:
    #             # f.write(f'Error synthesizing "{self.text}"\n')

    #             raise Exception(f'Error synthesizing "{self.text}"')
    #         else:
    #             synthesizer.save_wav(wav, path + '/tts_output.wav')

    #             segment = AudioSegment.from_wav(path + '/tts_output.wav')

    #             if self.strip_silence:
    #                 silence = detect_silence(segment, 100, -45)
    #                 segment = segment[:silence[-1][0]]
    #                 segment = segment.apply_gain(-20 - segment.dBFS)
    #                 # with open('/tmp/tts-rms.log', 'a+') as f:
    #                 #     f.write(f'{segment.rms}\n')

    #             audio += segment

    #         if self.pause_post > 0:
    #             audio += AudioSegment.silent(duration=self.pause_post)

    #     return audio


class TTS_Part:
    def __init__(self, tts_items: list = [], title: str = '', image_path: str = ''):
        self.tts_items = tts_items
        self.title = title
        self.image_path = image_path

    def get_character_count(self) -> int:
        count = 0

        for tts_item in self.tts_items:
            count += len(tts_item.text)
        return count


class TTS_Convert:
    # Speakers in preferred order (usually #0 and #1 for normal and quote speaker)
    # Best speakers: p293, p330, p273
    default_speakers = [
        'p273',
        'p330',
        'p234',
        'p270',
        'p280',
        'p308',
        'p312',
        'p318',
        'p225',
        'p226',
        'p227',
        'p228',
        'p229',
        'p230',
        'p231',
        'p232',
        'p233',
        'p236',
        'p237',
        'p238',
        'p239',
        'p240',
        'p241',
        'p243',
        'p244',
        'p245',
        'p246',
        'p247',
        'p248',
        'p249',
        'p250',
        'p251',
        'p252',
        'p253',
        'p254',
        'p255',
        'p256',
        'p257',
        'p258',
        'p259',
        'p260',
        'p261',
        'p262',
        'p263',
        'p264',
        'p265',
        'p266',
        'p267',
        'p268',
        'p269',
        'p271',
        'p272',
        'p293',
        'p274',
        'p275',
        'p276',
        'p277',
        'p278',
        'p279',
        'p281',
        'p282',
        'p283',
        'p284',
        'p285',
        'p286',
        'p287',
        'p288',
        'p292',
        'p294',
        'p295',
        'p297',
        'p298',
        'p299',
        'p300',
        'p301',
        'p302',
        'p303',
        'p304',
        'p305',
        'p306',
        'p307',
        'p310',
        'p311',
        'p313',
        'p314',
        'p316',
        'p317',
        'p323',
        'p326',
        'p329',
        'p333',
        'p334',
        'p335',
        'p336',
        'p339',
        'p340',
        'p341',
        'p343',
        'p345',
        'p347',
        'p351',
        'p360',
        'p361',
        'p362',
        'p363',
        'p364',
        'p374',
        'p376'
    ]

    # Break lines after number of characters to avoid OOM
    max_chars = 320

    def __init__(self, speakers=[str]) -> None:
        self.audio_all = AudioSegment.empty()

        self.model = 'tts_models/en/vctk/vits'

        # self.quotes = quotes
        self.current_speaker_idx = 0

        if speakers:
            self.default_speakers = speakers

    # def __del__(self):
    #     self.temp_dir.cleanup()
    #     self.synthesizer = None
    #     gc.collect()

    def initialize(self):
        log(LOG_TYPE.INFO, f'Initializing speech synthesizer')

        self.manager = ModelManager(os.path.dirname(TTS.__file__) + '/.models.json')
        #self.temp_dir = tempfile.TemporaryDirectory()

        with contextlib.redirect_stdout(None):
            model_path, config_path, model_item = self.manager.download_model(
                self.model)
            # vocoder_path, vocoder_config_path, _ = manager.download_model(model_item["default_vocoder"])

            self.synthesizer = Synthesizer(
                tts_checkpoint=model_path,
                tts_config_path=config_path,
                tts_speakers_file=None,
                tts_languages_file=None,
                vocoder_checkpoint=None,
                vocoder_config=None,
                encoder_checkpoint=None,
                encoder_config=None,
                use_cuda=False,
            )

    def _find_and_break(self, tts_items: list[TTS_Item], break_at: list[str], break_after: int) -> list[TTS_Item]:
        final_items = []

        for tts_item in tts_items:
            line = tts_item.text
            found = False

            if len(line) > break_after:
                for b in break_at:
                    find = line.rfind(b, 0, break_after)

                    if find >= 0:
                        final_items.append(TTS_Item(line[:find].strip(), tts_item.speaker, tts_item.pause_pre, tts_item.pause_post, tts_item.strip_silence))
                        final_items += self._find_and_break([TTS_Item(line[find + 1:].strip(), tts_item.speaker, tts_item.pause_pre,
                                                            tts_item.pause_post, tts_item.strip_silence)], break_at, break_after)
                        found = True
                        break

                if not found:
                    # No save spot for breaking found, do a hard break
                    final_items.append(TTS_Item(line[:break_after].strip(), tts_item.speaker, tts_item.pause_pre, tts_item.pause_post, tts_item.strip_silence))
                    final_items += self._find_and_break([TTS_Item(line[break_after:].strip(), tts_item.speaker, tts_item.pause_pre,
                                                        tts_item.pause_post, tts_item.strip_silence)], break_at, break_after)
            else:
                final_items.append(TTS_Item(line.strip(), tts_item.speaker, tts_item.pause_pre, tts_item.pause_post, tts_item.strip_silence))

        return final_items

    def _minimize_tailing_punctuation(self, text: str) -> str:
        lenght = 0

        for i in reversed(text):
            if i in string.punctuation + ' ':
                lenght += 1
            else:
                return text[:len(text) - (lenght - 1)]
        return text

    def prepare_item(self, tts_item: TTS_Item) -> list[TTS_Item]:
        pause_pre = tts_item.pause_pre
        pause_post = tts_item.pause_post

        # try:
        #     speaker_idx = TTS_Convert.default_speakers.index(tts_item.speaker)
        # except ValueError:
        #     log(LOG_TYPE.ERROR, f'Speaker index "{tts_item.speaker}" is unknown, falling back to default speaker.')
        #     speaker_idx = 0

        # Some general preprocessing

        text = tts_item.text

        text = text.replace(u'\xa0', ' ')
        text = re.sub(r'\.{3,}', r'', text)
        text = re.sub(r'\.+', r'.', text)
        text = re.sub(r'\?+', r'?', text)
        text = re.sub(r'\!+', r'!', text)
        # text = re.sub(r'[\(\)]', r'—', text)
        text = re.sub(r'…', r'', text)
        text = re.sub(r'[<>]\b', r'', text)

        # TODO: Find a more elegant solution
        text = re.sub(r'\bVIII\b', '8', text)
        text = re.sub(r'\bIII\b', '3', text)
        text = re.sub(r'\bVII\b', '7', text)
        text = re.sub(r'\bIV\b', '4', text)
        text = re.sub(r'\bVI\b', '6', text)
        text = re.sub(r'\bIX\b', '9', text)
        text = re.sub(r'\bII\b', '2', text)
        text = re.sub(r'\bV\b', '5', text)
        text = re.sub(r'\bX\b', '10', text)

        # Remove Japanese characters etc.
        text = ''.join(filter(lambda character: ord(character) < 0x3000, text))

        # Words
        text = re.sub(r'\bDOS\b', 'Dos', text)
        text = re.sub(r'\bDr.\b', 'Doctor', text)
        text = re.sub(r'\bMr.\b', 'Mister', text)
        text = re.sub(r'\bMs.\b', 'Miss', text)
        text = re.sub(r'\bMrs.\b', 'Misses', text)

        text = re.sub(r'\bST\b', 'Estea', text)

        # Text emojis
        text = re.sub(r'[:;][\(\)]', '', text)

        # Shorten URLs
        text = re.sub(r'(?:https?://)([^/]+)(?:\S+)', r'\1', text)

        tts_item.text = text

        tts_items = [tts_item]

        tts_items = self._break_single(tts_items, r'\n', pause_post=250)
        tts_items = self._break_single(tts_items, r'[\.!\?]\s', keep=True)
        tts_items = self._break_single(tts_items, r'[;:]\s', pause_post=150)
        tts_items = self._break_single(tts_items, r'[—–]', pause_post=150)
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

        tts_items = self._break_speakers(
            tts_items, ('(', ')'), pause_pre=300, pause_post=300)
        tts_items = self._break_speakers(
            tts_items, ('—', '—'), pause_pre=300, pause_post=300)
        tts_items = self._break_speakers(
            tts_items, ('– ', ' –'), pause_pre=300, pause_post=300)
        # tts_items = self.break_start_end(tts_items, ('- ', ' -'), pause_pre=300, pause_post=300)
        # tts_items = self.break_start_end(tts_items, (r'\s[-–—]-?\s', r'\s[-–—]-?\s'), pause_post=150)
        # tts_items = self.break_start_end(tts_items, (r'\(', r'\)'), pause_post=150)
        tts_items = self._break_speakers(tts_items, ('*', '*'))

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

            # Add a full stop if necessary
            # text = re.sub(r'([a-zA-Z0-9])$', r'\1.', text)

            if len(text) > 0:
                if text[-1] in ['.', ':', '!']:
                    tts_item.pause_post = 500
                elif text[-1] in ['?']:
                    tts_item.pause_post = 750
                tts_item.text = text

        if len(tts_items) > 0:
            tts_items[-1].pause_post += 500
            tts_items[-1].pause_pre += pause_pre
            tts_items[-1].pause_post += pause_post

        return tts_items

    def _break_single(self, tts_items: list[TTS_Item], break_at: str, keep: bool = False, strip_silence: bool = True, pause_post: int = 0) -> list[TTS_Item]:
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

                    # From last group to end of current group
                    final_items.append(TTS_Item(text[m.start():m.end() - length], tts_item.speaker, strip_silence=strip_silence, pause_post=pause_post))
                    last_start = m.end()

                # From end of last group to end of text
                text = text[last_start:].strip()

                if text:
                    final_items.append(TTS_Item(text, tts_item.speaker, tts_item.pause_pre, tts_item.pause_post, tts_item.strip_silence))

        return final_items

    def _get_character(self, text: str, pos: int) -> str:
        character = ''

        if pos > 0 and pos < len(text):
            character = text[pos]
        return character

    def _break_speakers(self, tts_items: list[TTS_Item], start_end: tuple = (), use_second_speaker: bool = False, pause_pre: int = 0, pause_post: int = 0) -> list[TTS_Item]:
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
                    new_item.speaker = tts_item.speaker
                    current_speaker = tts_item.speaker

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
                            new_item.pause_pre = pause_pre
                            new_item.pause_post = pause_post
                            final_items.append(new_item)
                            # print(f'Adding item after breaking: {new_item.text} / {new_item.speaker}')
                        pos = idx + 1

                # Add rest / regular item
                new_item = copy.copy(tts_item)
                new_item.text = tts_item.text[pos:].strip()
                new_item.speaker = current_speaker

                if new_item.text:
                    # print(f'Adding regular item: {new_item.text} / {new_item.speaker}')
                    final_items.append(new_item)

        return final_items

    # def speak_item(self, tts_item: TTS_Item) -> AudioSegment:
        
    #     try:
    #         return self.speak_tts_item(tts_item)
    #     except Exception as e:
    #         # with open(self.temp_dir.name + '/tts-error.log', 'a+') as f:
    #         #     f.write(f'Error synthesizing "{output_filename}"\n')
    #         log(LOG_TYPE.ERROR, f'Error synthesizing "{tts_item.text}"')
    #         sys.exit()

    def speak(self, tts_items: list[TTS_Item], output_filename: str, callback=None):
        final_items = []

        for tts_item in tts_items:
            if tts_item.text:
                # self.set_current_speaker(tts_item.speaker)
                final_items += self.prepare_item(tts_item)

        log(LOG_TYPE.INFO, f'{len(tts_items)} items broken down into {len(final_items)} items')

        time_total = 0.0
        time_needed = 0.0

        characters_sum = 0
        characters_total = 0

        for tts_item in final_items:
            characters_sum += len(tts_item.text)

        for idx, tts_item in enumerate(final_items):
            log(LOG_TYPE.INFO, f'Synthesizing item {idx + 1} of {len(final_items)} ({tts_item.speaker}, {tts_item.pause_pre}|{tts_item.pause_post}):{bcolors.ENDC} {tts_item.text}')

            if time_needed:
                log(LOG_TYPE.INFO, f'(Remaining time: {str(datetime.timedelta(seconds=round(time_needed)))})')

            time_last = time.time()

            try:
                self.speak_tts_item(tts_item)

                time_now = time.time()
                time_total += time_now - time_last
                characters_total += len(tts_item.text)

                time_needed = ((time_total / characters_total) * characters_sum) - time_total

                if callback:
                    # Report progress
                    callback(idx, len(final_items))
            except KeyboardInterrupt:
                log(LOG_TYPE.ERROR, 'Stopped by user.')
                sys.exit()
            except Exception as e:
                # with open(self.temp_dir.name + '/tts-error.log', 'a+') as f:
                #     f.write(f'Error synthesizing "{output_filename}"\n')
                log(LOG_TYPE.ERROR, f'Error synthesizing "{output_filename}"')
                sys.exit()

        self.export(output_filename)

    def numpy_to_segment(self, numpy_wav) -> AudioSegment:
        # Convert tts output wave into pydub segment
        wav = numpy.array(numpy_wav).astype(numpy.float32)
        wav_io = io.BytesIO()
        scipy.io.wavfile.write(wav_io, self.synthesizer.output_sample_rate, wav)
        wav_io.seek(0)
        return AudioSegment.from_wav(wav_io)

    def speak_tts_item(self, tts_item: TTS_Item) -> AudioSegment:
        segment = AudioSegment()
        if self.synthesizer is not None:
            if tts_item.pause_pre > 0:
                self.audio_all += AudioSegment.silent(duration=tts_item.pause_pre)

            # Check if line contains actual speech data
            if re.search(r'[a-zA-Z0-9]', tts_item.text):
                try:
                    # Suppress tts output
                    with contextlib.redirect_stdout(None):
                        wav = self.synthesizer.tts(
                            text=tts_item.text,
                            speaker_name=tts_item.speaker,
                            speaker_wav=None,
                            language_name=None,
                            reference_wav=None,
                            reference_speaker_name=None,
                        )
                except:
                    # with open(self.temp_dir.name + '/tts-error.log', 'a+') as f:
                    #     f.write(f'Error synthesizing "{tts_item.text}"\n')

                    raise Exception(f'Error synthesizing {tts_item.text}')
                else:

                    segment = self.numpy_to_segment(wav)

                    if tts_item.strip_silence:
                        silence = detect_silence(segment, min_silence_len=100, silence_thresh=-50)
                        segment = segment[:silence[-1][0]]
                        segment = segment.apply_gain(-20 - segment.dBFS)
                        # with open('/tmp/tts-rms.log', 'a+') as f:
                        #     f.write(f'{segment.rms}\n')

                    self.audio_all += segment

            if tts_item.pause_post > 0:
                self.audio_all += AudioSegment.silent(duration=tts_item.pause_post)

        return segment

    def segment_to_numpy(self, segment):
        samples = [s.get_array_of_samples() for s in segment.split_to_mono()]

        fp_arr = np.array(samples).T.astype(np.float64)
        fp_arr /= np.iinfo(samples[0].typecode).max

        return fp_arr

    def _compress(self, threshold: float, ratio: float, makeup: float, attack: float, release: float, segment: AudioSegment) -> AudioSegment:
        if ratio < 1.0:
            print('Ratio must be > 1.0 for compression to occur! You are expanding.')
        if ratio == 1.0:
            print('Signal is unaffected.')

        data = self.segment_to_numpy(segment)

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

        return self.numpy_to_segment(dataCs_bit)

    def export(self, output_filename: str) -> None:
        # Clean up to free up some memory
        # self.synthesizer = None
        # gc.collect()

        # Set default format to mp3
        format = 'mp3'

        file_format = os.path.splitext(output_filename)[1][1:]

        if file_format:
            format = file_format

        log(LOG_TYPE.INFO, f'Applying compression:')
        self.audio_all = self._compress(-20.0, 4.0, 4.5, 5.0, 15.0, self.audio_all)
        # self.audio = normalize(compress_dynamic_range(
        #     self.audio, threshold=-20, release=15))

        log(LOG_TYPE.INFO, f'Compressing, converting and saving as {output_filename}')
        audio_normalized = normalize(self.audio_all)

        if format == 'mp3':
            audio_normalized.export(output_filename, format=format, bitrate='320k')
        else:
            audio_normalized.export(output_filename, format=format)

        self.audio_all = AudioSegment.empty()
