import io

import numpy as np
import scipy.io.wavfile  # type: ignore
from pydub import AudioSegment  # type: ignore


def numpy_to_segment(numpy_wav: np.ndarray, sample_rate: int) -> AudioSegment:
    """
    Convert numpy array of audio samples to an AudioSegment object.

    :param numpy_wav: Numpy array of audio samples.
    :type numpy_wav: np.ndarray

    :param sample_rate: Sample rate of the audio data.
    :type sample_rate: int

    :return: The audio data as an AudioSegment object.
    :rtype: AudioSegment
    """
    wav = numpy_wav.astype(np.float32)
    wav_io = io.BytesIO()
    scipy.io.wavfile.write(wav_io, sample_rate, wav)
    wav_io.seek(0)
    return AudioSegment.from_wav(wav_io)


def segment_to_numpy(segment: AudioSegment) -> np.ndarray:
    """
    Convert an AudioSegment object to a numpy array of audio samples.

    :param segment: Audio data as an AudioSegment object.
    :type segment: AudioSegment

    :return: Numpy array of audio samples.
    :rtype: np.ndarray
    """
    samples = [s.get_array_of_samples() for s in segment.split_to_mono()]

    if samples:
        fp_arr = np.array(samples).T.astype(np.float64)
        fp_arr /= np.iinfo(samples[0].typecode).max
    else:
        fp_arr = np.array([])

    return fp_arr
