import io

import numpy as np
import scipy.io.wavfile
from pydub import AudioSegment


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
