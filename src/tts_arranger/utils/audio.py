import io

import numpy as np
import scipy.io.wavfile
from pydub import AudioSegment

from .log import LOG_TYPE, log


def numpy_to_segment(numpy_wav, sample_rate) -> AudioSegment:
    # Convert tts output wave into pydub segment
    wav = np.array(numpy_wav).astype(np.float32)
    wav_io = io.BytesIO()
    scipy.io.wavfile.write(wav_io, sample_rate, wav)
    wav_io.seek(0)
    return AudioSegment.from_wav(wav_io)


def segment_to_numpy(segment):
    samples = [s.get_array_of_samples() for s in segment.split_to_mono()]

    fp_arr = np.array(samples).T.astype(np.float64)
    fp_arr /= np.iinfo(samples[0].typecode).max

    return fp_arr


def compress(threshold: float, ratio: float, makeup: float, attack: float, release: float, segment: AudioSegment, sample_rate) -> AudioSegment:
    if ratio < 1.0:
        print('Ratio must be > 1.0 for compression to occur! You are expanding.')
    if ratio == 1.0:
        print('Signal is unaffected.')

    data = segment_to_numpy(segment)

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

    return numpy_to_segment(dataCs_bit, sample_rate)
